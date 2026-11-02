"""Quản lý trường hợp hỗ trợ.

Không có hàm tạo SupportCase ở đây: case chỉ được tạo khi giáo viên xác nhận cảnh báo
(review_service.confirm).
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import ensure_learner_access, get_learner_or_404, scope_by_learner
from app.models import CaseStatus, Followup, MetricResult, SupportCase, User
from app.schemas.support import SupportCaseUpdate
from app.services.pagination import PageParams
from app.services.review_service import learner_brief, validate_assignee

# Chỉ cho đi tiến: open → in_progress → closed, hoặc open → closed.
_ALLOWED_TRANSITIONS = {
    CaseStatus.OPEN: {CaseStatus.OPEN, CaseStatus.IN_PROGRESS, CaseStatus.CLOSED},
    CaseStatus.IN_PROGRESS: {CaseStatus.IN_PROGRESS, CaseStatus.CLOSED},
    CaseStatus.CLOSED: set(),
}

_CASE_LOAD = (
    selectinload(SupportCase.learner),
    selectinload(SupportCase.followups).selectinload(Followup.post_metric_result)
    .selectinload(MetricResult.metric_definition),
)


def followup_to_dict(followup: Followup) -> dict:
    post = followup.post_metric_result
    return {
        "id": followup.id,
        "case_id": followup.case_id,
        "action": followup.action,
        "outcome": followup.outcome,
        "result_status": followup.result_status,
        "post_metric_result_id": followup.post_metric_result_id,
        "post_metric_result": {
            "id": post.id, "value": post.value, "metric_code": post.metric_definition.code,
            "computed_at": post.computed_at,
        } if post else None,
        "performed_by": followup.performed_by,
        "performed_at": followup.performed_at,
    }


def case_to_dict(case: SupportCase, with_followups: bool = False) -> dict:
    data = {
        "id": case.id,
        "alert_id": case.alert_id,
        "learner": learner_brief(case.learner),
        "status": case.status,
        "reason": case.reason,
        "created_by": case.created_by,
        "assigned_to": case.assigned_to,
        "created_at": case.created_at,
        "closed_at": case.closed_at,
        "followup_count": len(case.followups),
    }
    if with_followups:
        data["followups"] = [followup_to_dict(f) for f in case.followups]
    return data


def get_case_for_user(db: Session, user: User, case_id: int) -> SupportCase:
    case = db.scalars(select(SupportCase).options(*_CASE_LOAD).where(SupportCase.id == case_id)).first()
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy trường hợp hỗ trợ")
    ensure_learner_access(db, user, case.learner_id)
    return case


def list_cases(db: Session, user: User, params: PageParams, status_filter: CaseStatus | None,
               learner_id: str | None, assigned_to: int | None) -> tuple[list[dict], int]:
    if learner_id is not None:
        get_learner_or_404(db, learner_id)
        ensure_learner_access(db, user, learner_id)

    stmt = select(SupportCase).options(*_CASE_LOAD) \
        .order_by(SupportCase.created_at.desc(), SupportCase.id.desc())
    stmt = scope_by_learner(stmt, SupportCase.learner_id, user)
    if status_filter is not None:
        stmt = stmt.where(SupportCase.status == status_filter)
    if learner_id is not None:
        stmt = stmt.where(SupportCase.learner_id == learner_id)
    if assigned_to is not None:
        stmt = stmt.where(SupportCase.assigned_to == assigned_to)

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    cases = db.scalars(stmt.offset(params.offset).limit(params.size)).all()
    return [case_to_dict(c) for c in cases], total


def update_case(db: Session, user: User, case_id: int, data: SupportCaseUpdate) -> SupportCase:
    case = get_case_for_user(db, user, case_id)
    if "assigned_to" in data.model_fields_set:
        validate_assignee(db, data.assigned_to)
    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Trường hợp đã đóng")
    if data.status is not None and data.status not in _ALLOWED_TRANSITIONS[case.status]:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail=f"Không thể chuyển trạng thái từ {case.status.value} sang {data.status.value}")

    if "assigned_to" in data.model_fields_set:
        case.assigned_to = data.assigned_to
    if data.status is not None and data.status != case.status:
        case.status = data.status
        if data.status == CaseStatus.CLOSED:
            case.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return get_case_for_user(db, user, case.id)
