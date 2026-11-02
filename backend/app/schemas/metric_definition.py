from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import FormulaType, MetricStatus
from app.schemas.common import ORMModel, UtcDatetime

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


# --- Tham số theo từng formula_type ------------------------------------------------

class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CumulativeGpaParams(_Strict):
    """GPA tích luỹ ở học kỳ gần nhất; không có tham số."""


class FailedCreditRatioParams(_Strict):
    terms: int = Field(default=1, gt=0)  # số học kỳ gần nhất được tính


FORMULA_PARAMS_MODELS: dict[FormulaType, type[BaseModel]] = {
    FormulaType.CUMULATIVE_GPA: CumulativeGpaParams,
    FormulaType.FAILED_CREDIT_RATIO: FailedCreditRatioParams,
}


class Threshold(_Strict):
    operator: Literal["<", "<=", ">", ">=", "=="]
    value: float


# --- Request / response ----------------------------------------------------------------

class MetricDefinitionCreate(BaseModel):
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    purpose: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""
    formula_type: FormulaType
    formula_params: dict
    threshold: Threshold


class MetricDefinitionUpdate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)] | None = None
    purpose: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    formula_params: dict | None = None
    threshold: Threshold | None = None


class ApproveRequest(BaseModel):
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = None


class RejectRequest(BaseModel):
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class MetricDefinitionOut(ORMModel):
    id: int
    code: str
    version: int
    name: str
    purpose: str
    formula_type: FormulaType
    formula_params: dict
    threshold: dict
    status: MetricStatus
    created_by: int | None
    approved_by: int | None
    approved_at: UtcDatetime | None
