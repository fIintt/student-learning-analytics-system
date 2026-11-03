from pydantic import AliasChoices, BaseModel, Field, StringConstraints, field_validator
from typing import Annotated
from app.schemas.common import ORMModel, UtcDatetime


class NewPassword(BaseModel):
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Mật khẩu không vượt quá 72 byte UTF-8")
        return value


class StudentAccountCreate(NewPassword):
    username: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=255, pattern=r"^\S+$")] = Field(validation_alias=AliasChoices("username", "email"))
    email: str | None = Field(default=None, min_length=3, max_length=255)
    student_id: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        if value is None:
            return None
        value = value.strip().lower()
        if value.count("@") != 1 or any(c.isspace() for c in value):
            raise ValueError("Email không hợp lệ")
        local, domain = value.split("@")
        if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("Email không hợp lệ")
        return value


class ChangePassword(NewPassword):
    current_password: str = Field(min_length=1, max_length=255)


class AccountStatus(BaseModel):
    is_active: bool


class TermOut(ORMModel):
    academic_year: str
    semester: int
    registered_credits: int
    passed_credits: int
    failed_credits: int
    semester_gpa: float
    cumulative_gpa: float


class TrendPoint(TermOut):
    gpa_change: float | None
    passed_percent: float | None
    failed_percent: float | None


class AcademicSummary(BaseModel):
    term_count: int
    latest: TrendPoint | None
    highest_semester_gpa: float | None
    lowest_semester_gpa: float | None
    trend: list[TrendPoint]


class StudentProfile(BaseModel):
    student_id: str
    name: str
    program_id: str
    program_name: str | None
    cohort: int
    academic_status: str


class StudentAlert(BaseModel):
    id: int
    status: str
    academic_year: str
    semester: int
    metric_code: str
    metric_name: str
    value: float | None
    threshold: dict
    created_at: UtcDatetime
    # Thông tin hỗ trợ cho sinh viên (null nếu cảnh báo chưa được giáo viên chuyển thành case).
    support_status: str | None = None
    advisor_name: str | None = None
    support_message: str | None = None
