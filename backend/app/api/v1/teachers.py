"""Admin quản lý phạm vi nhóm của tài khoản Giáo viên đã có."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.db.session import get_db
from app.models import LearnerGroup, Role, User
from app.schemas.auth import MeResponse
from app.schemas.common import Page
from app.schemas.teacher import TeacherGroupsUpdate
from app.services.auth_service import me
from app.services.pagination import PageParams, page_params, paginate

router = APIRouter(prefix="/admin/teacher-accounts", tags=["teacher-accounts"])
admin = require_roles(Role.ADMIN)


@router.get("", response_model=Page[MeResponse])
def list_teachers(params: PageParams = Depends(page_params), _admin: User = Depends(admin),
                  db: Session = Depends(get_db)):
    teachers, total = paginate(db, select(User).where(User.role == Role.REVIEWER).order_by(User.id), params)
    return Page(items=[me(db, teacher) for teacher in teachers], total=total, page=params.page, size=params.size)


@router.put("/{user_id}/groups", response_model=MeResponse)
def replace_groups(user_id: int, body: TeacherGroupsUpdate, _admin: User = Depends(admin),
                   db: Session = Depends(get_db)):
    # Lock the teacher so overlapping replacements cannot merge accidentally.
    teacher = db.scalar(select(User).where(User.id == user_id).with_for_update()
                        .execution_options(populate_existing=True))
    if teacher is None:
        raise HTTPException(404, detail="Không tìm thấy tài khoản")
    if teacher.role != Role.REVIEWER:
        raise HTTPException(400, detail="Chỉ gán nhóm cho tài khoản Giáo viên")
    groups = list(db.scalars(select(LearnerGroup).where(LearnerGroup.id.in_(body.group_ids))
                            .order_by(LearnerGroup.id)).all())
    if len(groups) != len(body.group_ids):
        raise HTTPException(400, detail="Danh sách chứa nhóm không tồn tại")
    teacher.groups = groups
    db.commit()
    return me(db, teacher)
