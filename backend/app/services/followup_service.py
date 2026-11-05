"""Theo dõi sau can thiệp: ghi hành động, kết quả và (tuỳ chọn) chỉ số đo lại sau can thiệp."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import scope_by_learner
from app.models import CaseStatus, Followup, MetricResult, SupportCase, User
from app.schemas.support import FollowupCreate
from app.services.case_service import followup_to_dict, get_case_for_user
from app.services.pagination import PageParams

_FOLLOWUP_LOAD = (selectinload(Followup.post_metric_result).selectinload(MetricResult.metric_definition),)


def create_followup(db: Session, user: User, data: FollowupCreate) -> dict:
    case = get_case_for_user(db, user, data.case_id)
    if not data.action:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Phải mô tả hành động can thiệp")
    if data.post_metric_result_id is not None:
        post = db.get(MetricResult, data.post_metric_result_id)
        if post is None or post.learner_id != case.learner_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                detail="Kết quả chỉ số sau can thiệp phải thuộc cùng người học của trường hợp")
    if case.status == CaseStatus.CLOSED:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Trường hợp đã đóng")

    followup = Followup(case_id=case.id, action=data.action, outcome=data.outcome or None,
                        result_status=data.result_status, post_metric_result_id=data.post_metric_result_id,
                        performed_by=user.id)
    db.add(followup)
    db.commit()
    followup = db.scalars(select(Followup).options(*_FOLLOWUP_LOAD).where(Followup.id == followup.id)).one()
    return followup_to_dict(followup)


def list_followups(db: Session, user: User, params: PageParams, case_id: int | None) -> tuple[list[dict], int]:
    if case_id is not None:
        get_case_for_user(db, user, case_id)

    stmt = (select(Followup).options(*_FOLLOWUP_LOAD)
            .join(SupportCase, SupportCase.id == Followup.case_id)
            .order_by(Followup.performed_at.desc(), Followup.id.desc()))
    stmt = scope_by_learner(stmt, SupportCase.learner_id, user)
    if case_id is not None:
        stmt = stmt.where(Followup.case_id == case_id)

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.offset(params.offset).limit(params.size)).all()
    return [followup_to_dict(f) for f in items], total
