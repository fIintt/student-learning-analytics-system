"""Danh sách chỉ đọc cho giao diện (bộ lọc, bảng sinh viên). Dành cho admin/Giáo viên, luôn lọc theo phạm vi quyền."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.db.session import get_db
from app.models import Role, User
from app.schemas.catalog import GroupOut, LearnerListItem, ProgramOut
from app.schemas.common import Page
from app.services import catalog_service
from app.services.pagination import PageParams, page_params

router = APIRouter(tags=["catalog"])
staff = require_roles(Role.ADMIN, Role.REVIEWER)


@router.get("/groups", response_model=Page[GroupOut])
def list_groups(params: PageParams = Depends(page_params), user: User = Depends(staff),
                db: Session = Depends(get_db)):
    items, total = catalog_service.list_groups(db, user, params)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.get("/learners", response_model=Page[LearnerListItem])
def list_learners(
    group_id: int | None = None,
    program_id: str | None = None,
    cohort: int | None = None,
    q: str | None = None,
    params: PageParams = Depends(page_params),
    user: User = Depends(staff),
    db: Session = Depends(get_db),
):
    items, total = catalog_service.list_learners(db, user, params, group_id, program_id, cohort, q)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.get("/programs", response_model=Page[ProgramOut])
def list_programs(params: PageParams = Depends(page_params), user: User = Depends(staff),
                  db: Session = Depends(get_db)):
    items, total = catalog_service.list_programs(db, user, params)
    return Page(items=items, total=total, page=params.page, size=params.size)
