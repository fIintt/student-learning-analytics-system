"""Phân quyền theo vai trò và phạm vi nhóm sinh viên.

- admin: thấy mọi sinh viên.
- reviewer, viewer: chỉ thấy sinh viên thuộc các nhóm được gán trong user_group_access.
  Sinh viên thuộc nhóm khi cùng chương trình (program_id) và cùng khoá (cohort) với nhóm đó.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.models import LearnerGroup, Role, Student, User, user_group_access


def require_roles(*roles: Role):
    allowed = set(roles)

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền thực hiện thao tác này")
        return user

    return _dependency


def has_full_access(user: User) -> bool:
    return user.role == Role.ADMIN


def accessible_group_ids(db: Session, user: User) -> list[int]:
    """Danh sách id nhóm user được xem (admin: mọi nhóm)."""
    if has_full_access(user):
        stmt = select(LearnerGroup.id)
    else:
        stmt = select(user_group_access.c.group_id).where(user_group_access.c.user_id == user.id)
    return sorted(db.scalars(stmt).all())


def accessible_learner_ids_subquery(user: User):
    """Subquery mã sinh viên trong phạm vi user; None nghĩa là không giới hạn (admin)."""
    if has_full_access(user):
        return None
    return (
        select(Student.student_id)
        .join(LearnerGroup, (LearnerGroup.program_id == Student.program_id)
              & (LearnerGroup.cohort == Student.cohort))
        .join(user_group_access, user_group_access.c.group_id == LearnerGroup.id)
        .where(user_group_access.c.user_id == user.id)
    )


def scope_by_learner(stmt: Select, learner_id_column, user: User) -> Select:
    """Thêm điều kiện lọc theo phạm vi nhóm vào một câu select có cột mã sinh viên."""
    subq = accessible_learner_ids_subquery(user)
    if subq is None:
        return stmt
    return stmt.where(learner_id_column.in_(subq))


def can_access_learner(db: Session, user: User, learner_id: str) -> bool:
    if has_full_access(user):
        return True
    subq = accessible_learner_ids_subquery(user).where(Student.student_id == learner_id)
    return db.scalars(subq.limit(1)).first() is not None


def ensure_learner_access(db: Session, user: User, learner_id: str) -> None:
    if not can_access_learner(db, user, learner_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền xem người học này")


def ensure_group_access(db: Session, user: User, group_id: int) -> None:
    if has_full_access(user):
        return
    if group_id not in accessible_group_ids(db, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền xem nhóm này")


def get_learner_or_404(db: Session, learner_id: str) -> Student:
    student = db.get(Student, learner_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người học")
    return student
