import enum

from sqlalchemy import Enum as SAEnum


def str_enum(enum_cls: type[enum.Enum]) -> SAEnum:
    """Lưu enum dạng VARCHAR theo giá trị (chữ thường), không tạo kiểu ENUM riêng."""
    return SAEnum(enum_cls, native_enum=False, create_constraint=False,
                  values_callable=lambda e: [m.value for m in e], validate_strings=True)


class Role(str, enum.Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    VIEWER = "viewer"

    @property
    def label(self) -> str:
        return {"admin": "admin", "reviewer": "Giáo viên", "viewer": "Sinh viên"}[self.value]


class AcademicStatus(str, enum.Enum):
    STUDYING = "studying"
    GRADUATED = "graduated"
    SUSPENDED = "suspended"


class MetricStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETIRED = "retired"


class FormulaType(str, enum.Enum):
    CUMULATIVE_GPA = "cumulative_gpa"
    FAILED_CREDIT_RATIO = "failed_credit_ratio"


class AlertStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    SUPERSEDED = "superseded"


class CaseStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class ResultStatus(str, enum.Enum):
    UNKNOWN = "unknown"
    IMPROVED = "improved"
    NO_CHANGE = "no_change"
    WORSENED = "worsened"
