"""Trường hợp hỗ trợ. Cố ý KHÔNG có POST: case chỉ sinh ra từ /review/alerts/{id}/confirm."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.db.session import get_db
from app.models import CaseStatus, Role, User
from app.schemas.common import Page
from app.schemas.support import SupportCaseDetailOut, SupportCaseOut, SupportCaseUpdate
from app.services import case_service
from app.services.pagination import PageParams, page_params

router = APIRouter(prefix="/support-cases", tags=["support-cases"])
staff = require_roles(Role.ADMIN, Role.REVIEWER)


@router.get("", response_model=Page[SupportCaseOut])
def list_cases(
    status_filter: CaseStatus | None = Query(None, alias="status"),
    learner_id: str | None = None,
    assigned_to: int | None = None,
    params: PageParams = Depends(page_params),
    user: User = Depends(staff),
    db: Session = Depends(get_db),
):
    items, total = case_service.list_cases(db, user, params, status_filter, learner_id, assigned_to)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.get("/{case_id}", response_model=SupportCaseDetailOut)
def get_case(case_id: int, user: User = Depends(staff), db: Session = Depends(get_db)):
    return case_service.case_to_dict(case_service.get_case_for_user(db, user, case_id), with_followups=True)


@router.patch("/{case_id}", response_model=SupportCaseDetailOut)
def update_case(case_id: int, body: SupportCaseUpdate, user: User = Depends(staff),
                db: Session = Depends(get_db)):
    return case_service.case_to_dict(case_service.update_case(db, user, case_id, body), with_followups=True)
