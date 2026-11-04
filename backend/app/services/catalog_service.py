"""Danh sách chỉ đọc cho giao diện: nhóm, sinh viên, chương trình. Luôn lọc theo phạm vi của người xem."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import accessible_group_ids, ensure_group_access, has_full_access, scope_by_learner
from app.models import LearnerGroup, Program, Student, User
from app.services.pagination import PageParams, paginate


def list_groups(db: Session, user: User, params: PageParams) -> tuple[list[dict], int]:
    learner_count = (select(func.count())
                     .where(Student.program_id == LearnerGroup.program_id, Student.cohort == LearnerGroup.cohort)
                     .correlate(LearnerGroup).scalar_subquery())
    stmt = (select(LearnerGroup, Program.program_name_vi, learner_count)
            .join(Program, Program.program_id == LearnerGroup.program_id)
            .order_by(LearnerGroup.name))
    if not has_full_access(user):
        stmt = stmt.where(LearnerGroup.id.in_(accessible_group_ids(db, user)))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(stmt.offset(params.offset).limit(params.size)).all()
    return [{"id": g.id, "name": g.name, "program_id": g.program_id, "program_name": program_name,
             "cohort": g.cohort, "learner_count": count} for g, program_name, count in rows], total


def list_learners(db: Session, user: User, params: PageParams, group_id: int | None, program_id: str | None,
                  cohort: int | None, q: str | None) -> tuple[list[dict], int]:
    stmt = (select(Student, Program.program_name_vi)
            .join(Program, Program.program_id == Student.program_id)
            .order_by(Student.student_id))
    stmt = scope_by_learner(stmt, Student.student_id, user)

    if group_id is not None:
        group = db.get(LearnerGroup, group_id)
        if group is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhóm")
        ensure_group_access(db, user, group_id)
        stmt = stmt.where(Student.program_id == group.program_id, Student.cohort == group.cohort)
    if program_id:
        stmt = stmt.where(Student.program_id == program_id)
    if cohort is not None:
        stmt = stmt.where(Student.cohort == cohort)
    if q and q.strip():
        text = q.strip()
        stmt = stmt.where(func.lower(Student.name).contains(text.lower(), autoescape=True)
                          | Student.student_id.startswith(text, autoescape=True))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(stmt.offset(params.offset).limit(params.size)).all()
    return [{"id": s.student_id, "full_name": s.name, "program_id": s.program_id, "program_name": program_name,
             "cohort": s.cohort, "academic_status": s.academic_status} for s, program_name in rows], total


def list_programs(db: Session, user: User, params: PageParams) -> tuple[list[dict], int]:
    """Admin: mọi chương trình. Người khác: chương trình có sinh viên nằm trong phạm vi của họ."""
    stmt = select(Program).order_by(Program.program_id)
    if not has_full_access(user):
        stmt = stmt.where(Program.program_id.in_(scope_by_learner(select(Student.program_id),
                                                                  Student.student_id, user)))
    programs, total = paginate(db, stmt, params)
    return [{"id": p.program_id, "name": p.program_name_vi, "name_en": p.program_name_en,
             "program_type": p.program_type, "first_cohort_year": p.first_cohort_year,
             "last_cohort_year": p.last_cohort_year} for p in programs], total
