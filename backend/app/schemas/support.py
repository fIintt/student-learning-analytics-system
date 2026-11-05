from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.models import AlertStatus, CaseStatus, ResultStatus
from app.schemas.common import UtcDatetime

# Trường bắt buộc (note, reason, action) để Optional ở schema và kiểm tra trong service,
# để thứ tự lỗi đúng contract: 404 → 403 (phạm vi) → 400 → 409.
Text1000 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class LearnerBrief(BaseModel):
    id: str  # mã sinh viên
    full_name: str | None


class AlertMetricResult(BaseModel):
    id: int
    value: float | None
    metric_code: str
    metric_version: int
    academic_year: str
    semester: int
    threshold: dict
    computed_at: UtcDatetime


class AlertOut(BaseModel):
    id: int
    status: AlertStatus
    learner: LearnerBrief
    metric_result: AlertMetricResult
    reviewer_id: int | None
    review_note: str | None
    created_at: UtcDatetime
    reviewed_at: UtcDatetime | None
    support_case_id: int | None


class ConfirmRequest(BaseModel):
    note: Text1000 | None = None
    reason: Text1000 | None = None
    assigned_to: int | None = None


class DismissRequest(BaseModel):
    note: Text1000 | None = None


class SupportCaseOut(BaseModel):
    id: int
    alert_id: int
    learner: LearnerBrief
    status: CaseStatus
    reason: str
    created_by: int
    assigned_to: int | None
    created_at: UtcDatetime
    closed_at: UtcDatetime | None
    followup_count: int


class ConfirmResponse(BaseModel):
    alert: AlertOut
    support_case: SupportCaseOut


class SupportCaseUpdate(BaseModel):
    status: CaseStatus | None = None
    assigned_to: int | None = None


class FollowupMetricResult(BaseModel):
    id: int
    value: float | None
    metric_code: str
    computed_at: UtcDatetime


class FollowupOut(BaseModel):
    id: int
    case_id: int
    action: str
    outcome: str | None
    result_status: ResultStatus
    post_metric_result_id: int | None
    post_metric_result: FollowupMetricResult | None
    performed_by: int
    performed_at: UtcDatetime


class SupportCaseDetailOut(SupportCaseOut):
    followups: list[FollowupOut]


class FollowupCreate(BaseModel):
    case_id: int
    action: Text1000 | None = None
    outcome: Text1000 | None = None
    result_status: ResultStatus = ResultStatus.UNKNOWN
    post_metric_result_id: int | None = None
