"""Nhóm phân quyền: mỗi chương trình × khoá có trong bảng students là một nhóm.

Bảng students do pipeline nạp, nên nhóm được đồng bộ từ đó (khi khởi động backend hoặc khi chạy seed).
Chỉ thêm nhóm mới, không xoá hay đổi nhóm đã có để không làm mất phân quyền đã gán.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LearnerGroup, Program, Student


def sync_groups(db: Session) -> int:
    """Tạo các nhóm còn thiếu; trả về số nhóm mới."""
    pairs = set(db.execute(select(Student.program_id, Student.cohort).distinct()).all())
    existing = {(g.program_id, g.cohort) for g in db.scalars(select(LearnerGroup))}
    missing = sorted(pairs - existing)
    if not missing:
        return 0

    names = dict(db.execute(select(Program.program_id, Program.program_name_vi)).all())
    for program_id, cohort in missing:
        db.add(LearnerGroup(name=f"{program_id}-{cohort}", program_id=program_id, cohort=cohort,
                            description=f"{names.get(program_id, program_id)} - Khoá {cohort}"))
    db.commit()
    return len(missing)
