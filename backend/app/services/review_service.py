"""Giáo viên rà soát cảnh báo.

Đây là NƠI DUY NHẤT tạo SupportCase: chỉ khi người dùng xác nhận (confirm) một Alert
đang pending_review. Hệ thống không tự ra quyết định nào từ cảnh báo.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import ensure_learner_access, get_learner_or_404, scope_by_learner
from app.models import Alert, AlertStatus, CaseStatus, MetricResult, Role, SupportCase, User
from app.schemas.support import ConfirmRequest, DismissRequest
from app.services import audit_service
from app.services.pagination import PageParams


def learner_brief(student) -> dict:
    return {"id": student.student_id, "full_name": student.name}


def alert_to_dict(alert: Alert) -> dict:
    result = alert.metric_result
    definition = result.metric_definition
    return {
        "id": alert.id,
        "status": alert.status,
        "learner": learner_brief(alert.learner),
        "metric_result": {
            "id": result.id, "value": result.value, "metric_code": definition.code,
            "metric_version": definition.version, "academic_year": result.academic_year,
            "semester": result.semester,
            "threshold": definition.threshold, "computed_at": result.computed_at,
        },
        "reviewer_id": alert.reviewer_id,
        "review_note": alert.review_note,
        "created_at": alert.created_at,
        "reviewed_at": alert.reviewed_at,
        "support_case_id": alert.support_case.id if alert.support_case else None,
    }


_ALERT_LOAD = (
    selectinload(Alert.learner),
    selectinload(Alert.support_case),
    selectinload(Alert.metric_result).selectinload(MetricResult.metric_definition),
)


def get_alert_for_user(db: Session, user: User, alert_id: int) -> Alert:
    alert = db.scalars(select(Alert).options(*_ALERT_LOAD).where(Alert.id == alert_id)).first()
    if alert is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cảnh báo")
    ensure_learner_access(db, user, alert.learner_id)
    return alert


def list_alerts(db: Session, user: User, params: PageParams, status_filter: AlertStatus | None,
                learner_id: str | None, metric_definition_id: int | None) -> tuple[list[dict], int]:
    if learner_id is not None:
        get_learner_or_404(db, learner_id)
        ensure_learner_access(db, user, learner_id)

    stmt = select(Alert).options(*_ALERT_LOAD).order_by(Alert.created_at.desc(), Alert.id.desc())
    stmt = scope_by_learner(stmt, Alert.learner_id, user)
    if status_filter is not None:
        stmt = stmt.where(Alert.status == status_filter)
    if learner_id is not None:
        stmt = stmt.where(Alert.learner_id == learner_id)
    if metric_definition_id is not None:
        stmt = stmt.join(MetricResult, MetricResult.id == Alert.metric_result_id) \
            .where(MetricResult.metric_definition_id == metric_definition_id)

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    alerts = db.scalars(stmt.offset(params.offset).limit(params.size)).all()
    return [alert_to_dict(a) for a in alerts], total


def validate_assignee(db: Session, user_id: int | None) -> None:
    if user_id is None:
        return
    assignee = db.get(User, user_id)
    if assignee is None or not assignee.is_active or assignee.role not in (Role.ADMIN, Role.REVIEWER):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            detail="Người được giao phải là tài khoản admin hoặc reviewer đang hoạt động")


def _mark_reviewed(db: Session, alert: Alert, user: User, new_status: AlertStatus, note: str) -> datetime:
    """Chuyển trạng thái có điều kiện, để hai người xử lý cùng lúc thì chỉ một người thành công."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = db.execute(
        update(Alert)
        .where(Alert.id == alert.id, Alert.status == AlertStatus.PENDING_REVIEW)
        .values(status=new_status, reviewer_id=user.id, review_note=note, reviewed_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Cảnh báo đã được xử lý")
    return now


def _require_text(value: str | None, message: str) -> str:
    if not value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=message)
    return value


def confirm(db: Session, user: User, alert_id: int, data: ConfirmRequest) -> tuple[Alert, SupportCase]:
    alert = get_alert_for_user(db, user, alert_id)
    note = _require_text(data.note, "Phải nhập ghi chú khi xác nhận cảnh báo")
    reason = _require_text(data.reason, "Phải nêu lý do cần hỗ trợ khi xác nhận cảnh báo")
    validate_assignee(db, data.assigned_to)
    if alert.status != AlertStatus.PENDING_REVIEW:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Cảnh báo đã được xử lý")

    try:
        _mark_reviewed(db, alert, user, AlertStatus.CONFIRMED, note)
        case = SupportCase(alert_id=alert.id, learner_id=alert.learner_id, status=CaseStatus.OPEN,
                           reason=reason, created_by=user.id, assigned_to=data.assigned_to)
        db.add(case)
        db.flush()
        audit_service.record(db, user, audit_service.ALERT_CONFIRM, audit_service.ALERT, alert.id,
                             {"note": note, "reason": reason, "support_case_id": case.id})
        audit_service.record(db, user, audit_service.CASE_CREATE, audit_service.SUPPORT_CASE, case.id,
                             {"alert_id": alert.id, "learner_id": alert.learner_id,
                              "assigned_to": data.assigned_to})
        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise

    db.expire_all()  # alert đã đổi bằng UPDATE trực tiếp, nạp lại từ DB
    return get_alert_for_user(db, user, alert.id), case


def dismiss(db: Session, user: User, alert_id: int, data: DismissRequest) -> Alert:
    alert = get_alert_for_user(db, user, alert_id)
    note = _require_text(data.note, "Phải nhập ghi chú khi bác cảnh báo")
    if alert.status != AlertStatus.PENDING_REVIEW:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Cảnh báo đã được xử lý")

    _mark_reviewed(db, alert, user, AlertStatus.DISMISSED, note)
    audit_service.record(db, user, audit_service.ALERT_DISMISS, audit_service.ALERT, alert.id, {"note": note})
    db.commit()
    db.expire_all()
    return get_alert_for_user(db, user, alert.id)
