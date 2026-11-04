from typing import Literal

from pydantic import BaseModel

from app.models import AcademicStatus, CaseStatus, ResultStatus
from app.schemas.common import UtcDatetime


class IdName(BaseModel):
    id: int
    name: str


class ProgramBrief(BaseModel):
    id: str  # mã chương trình
    name: str
    name_en: str | None
    program_type: str | None


class LearnerInfo(BaseModel):
    id: str  # mã sinh viên
    full_name: str | None
    program: ProgramBrief | None
    cohort: int | None
    academic_status: AcademicStatus | None
    groups: list[IdName]


class MetricHistoryItem(BaseModel):
    value: float | None
    computed_at: UtcDatetime
    academic_year: str
    semester: int
    metric_version: int


class LearnerMetric(BaseModel):
    metric_code: str
    metric_version: int
    latest_value: float | None
    flagged: bool
    computed_at: UtcDatetime
    academic_year: str
    semester: int
    history: list[MetricHistoryItem]


class LearnerCaseItem(BaseModel):
    id: int
    status: CaseStatus
    reason: str
    created_at: UtcDatetime
    followup_count: int
    latest_result_status: ResultStatus | None


class LearnerReport(BaseModel):
    learner: LearnerInfo
    metrics: list[LearnerMetric]
    alerts: dict[str, int]
    support_cases: list[LearnerCaseItem]


class ReportScope(BaseModel):
    type: Literal["group", "program"]
    id: int | str  # nhóm: số; chương trình: mã chuỗi
    name: str


class AggregateMetric(BaseModel):
    metric_code: str
    metric_version: int
    learners_with_result: int
    avg_value: float | None
    min_value: float | None
    max_value: float | None
    flagged_count: int
    flagged_ratio: float


class LearnerNeedingSupport(BaseModel):
    id: str  # mã sinh viên
    full_name: str | None
    flagged_metrics: list[str]
    open_case: bool


class AggregateReport(BaseModel):
    scope: ReportScope
    learner_count: int
    metrics: list[AggregateMetric]
    alerts: dict[str, int]
    support_cases: dict[str, int]
    followups: dict[str, int]
    learners_needing_support: list[LearnerNeedingSupport]
