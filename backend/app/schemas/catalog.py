from pydantic import BaseModel

from app.models import AcademicStatus


class GroupOut(BaseModel):
    id: int
    name: str
    program_id: str
    program_name: str
    cohort: int
    learner_count: int


class LearnerListItem(BaseModel):
    id: str  # mã sinh viên
    full_name: str
    program_id: str
    program_name: str
    cohort: int
    academic_status: AcademicStatus


class ProgramOut(BaseModel):
    id: str  # mã chương trình
    name: str
    name_en: str
    program_type: str
    first_cohort_year: int
    last_cohort_year: int
