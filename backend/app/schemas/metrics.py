from pydantic import BaseModel

from app.schemas.common import UtcDatetime


class ComputeRequest(BaseModel):
    metric_definition_id: int


class ComputeResponse(BaseModel):
    metric_definition_id: int
    metric_code: str
    metric_version: int
    computed_at: UtcDatetime
    learners_computed: int
    learners_skipped: int
    flagged: int
    alerts_created: int


class MetricResultOut(BaseModel):
    id: int
    learner_id: str
    learner_name: str | None
    metric_definition_id: int
    metric_code: str
    metric_version: int
    academic_year: str
    semester: int
    value: float | None
    flagged: bool
    threshold: dict
    computed_at: UtcDatetime
