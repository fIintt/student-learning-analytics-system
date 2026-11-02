"""Vòng đời công thức chỉ số: draft → pending → approved | rejected.

- Chỉ admin được approve/reject (chặn ở router bằng require_roles).
- Công thức đã duyệt không bị sửa; muốn đổi phải tạo version mới qua new-version.
- Approve một version mới sẽ chuyển version approved cũ cùng code sang retired.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FormulaType, MetricDefinition, MetricStatus, User
from app.schemas.metric_definition import (
    FORMULA_PARAMS_MODELS,
    MetricDefinitionCreate,
    MetricDefinitionUpdate,
)
from app.services import audit_service
from app.services.pagination import PageParams, paginate

_EDITABLE = {MetricStatus.DRAFT, MetricStatus.REJECTED}


def _conflict(message: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail=message)


def validate_formula_params(formula_type: FormulaType | str, params: dict) -> dict:
    """Kiểm tra params theo formula_type; trả về params đã chuẩn hoá. Sai → 400."""
    model = FORMULA_PARAMS_MODELS[FormulaType(formula_type)]
    try:
        return model.model_validate(params).model_dump(exclude_none=True)
    except ValidationError as exc:
        err = exc.errors()[0]
        field = ".".join(str(p) for p in err["loc"]) or "formula_params"
        reason = {
            "missing": "thiếu tham số bắt buộc",
            "extra_forbidden": "tham số không được hỗ trợ",
            "greater_than": "phải lớn hơn 0",
            "int_parsing": "phải là số nguyên",
            "int_type": "phải là số nguyên",
            "int_from_float": "phải là số nguyên",
            "string_too_short": "không được để trống",
            "list_type": "phải là danh sách",
        }.get(err["type"], "giá trị không hợp lệ")
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Tham số công thức không hợp lệ cho loại {FormulaType(formula_type).value}: "
                   f"'{field}' {reason}",
        )


def get_or_404(db: Session, definition_id: int) -> MetricDefinition:
    definition = db.get(MetricDefinition, definition_id)
    if definition is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy công thức chỉ số")
    return definition


def list_definitions(db: Session, params: PageParams, status_filter: MetricStatus | None,
                     code: str | None) -> tuple[list[MetricDefinition], int]:
    stmt = select(MetricDefinition).order_by(MetricDefinition.code, MetricDefinition.version.desc())
    if status_filter is not None:
        stmt = stmt.where(MetricDefinition.status == status_filter)
    if code:
        stmt = stmt.where(MetricDefinition.code == code.strip())
    return paginate(db, stmt, params)


def create(db: Session, user: User, data: MetricDefinitionCreate) -> MetricDefinition:
    params = validate_formula_params(data.formula_type, data.formula_params)
    if db.scalar(select(MetricDefinition.id).where(MetricDefinition.code == data.code).limit(1)):
        raise _conflict("Mã công thức đã tồn tại")
    definition = MetricDefinition(
        code=data.code, version=1, name=data.name, purpose=data.purpose,
        formula_type=data.formula_type.value, formula_params=params,
        threshold=data.threshold.model_dump(), status=MetricStatus.DRAFT, created_by=user.id,
    )
    db.add(definition)
    db.commit()
    return definition


def _apply_changes(definition: MetricDefinition, data: MetricDefinitionUpdate) -> None:
    if data.formula_params is not None:
        definition.formula_params = validate_formula_params(definition.formula_type, data.formula_params)
    if data.name is not None:
        definition.name = data.name
    if data.purpose is not None:
        definition.purpose = data.purpose
    if data.threshold is not None:
        definition.threshold = data.threshold.model_dump()


def update(db: Session, definition_id: int, data: MetricDefinitionUpdate) -> MetricDefinition:
    definition = get_or_404(db, definition_id)
    if data.formula_params is not None:
        validate_formula_params(definition.formula_type, data.formula_params)
    if definition.status not in _EDITABLE:
        raise _conflict("Chỉ sửa được công thức ở trạng thái nháp hoặc bị từ chối")
    _apply_changes(definition, data)
    definition.status = MetricStatus.DRAFT
    db.commit()
    return definition


def submit(db: Session, definition_id: int) -> MetricDefinition:
    definition = get_or_404(db, definition_id)
    if not (definition.purpose or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Phải nêu mục đích sử dụng trước khi gửi duyệt")
    if definition.status != MetricStatus.DRAFT:
        raise _conflict("Chỉ gửi duyệt được công thức ở trạng thái nháp")
    definition.status = MetricStatus.PENDING
    db.commit()
    return definition


def approve(db: Session, admin: User, definition_id: int, note: str | None = None) -> MetricDefinition:
    definition = get_or_404(db, definition_id)
    if definition.status != MetricStatus.PENDING:
        raise _conflict("Chỉ phê duyệt được công thức đang chờ duyệt")

    previous = db.scalars(select(MetricDefinition).where(
        MetricDefinition.code == definition.code,
        MetricDefinition.status == MetricStatus.APPROVED,
        MetricDefinition.id != definition.id,
    )).all()
    for old in previous:
        old.status = MetricStatus.RETIRED

    definition.status = MetricStatus.APPROVED
    definition.approved_by = admin.id
    definition.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    audit_service.record(db, admin, audit_service.METRIC_APPROVE, audit_service.METRIC_DEFINITION, definition.id, {
        "code": definition.code, "version": definition.version, "note": note,
        "retired_ids": [old.id for old in previous],
    })
    db.commit()
    return definition


def reject(db: Session, admin: User, definition_id: int, note: str) -> MetricDefinition:
    definition = get_or_404(db, definition_id)
    if definition.status != MetricStatus.PENDING:
        raise _conflict("Chỉ từ chối được công thức đang chờ duyệt")
    definition.status = MetricStatus.REJECTED
    audit_service.record(db, admin, audit_service.METRIC_REJECT, audit_service.METRIC_DEFINITION, definition.id,
                         {"code": definition.code, "version": definition.version, "note": note})
    db.commit()
    return definition


def new_version(db: Session, user: User, definition_id: int, data: MetricDefinitionUpdate) -> MetricDefinition:
    source = get_or_404(db, definition_id)
    if data.formula_params is not None:
        validate_formula_params(source.formula_type, data.formula_params)
    if source.status != MetricStatus.APPROVED:
        raise _conflict("Chỉ tạo phiên bản mới từ công thức đã được phê duyệt")
    in_progress = db.scalar(select(MetricDefinition.id).where(
        MetricDefinition.code == source.code,
        MetricDefinition.status.in_([MetricStatus.DRAFT, MetricStatus.PENDING]),
    ).limit(1))
    if in_progress:
        raise _conflict("Công thức này đã có phiên bản mới đang soạn hoặc chờ duyệt")

    max_version = db.scalar(select(func.max(MetricDefinition.version))
                            .where(MetricDefinition.code == source.code)) or 0
    definition = MetricDefinition(
        code=source.code, version=max_version + 1, name=source.name, purpose=source.purpose,
        formula_type=source.formula_type, formula_params=dict(source.formula_params),
        threshold=dict(source.threshold), status=MetricStatus.DRAFT, created_by=user.id,
    )
    _apply_changes(definition, data)
    db.add(definition)
    db.commit()
    return definition
