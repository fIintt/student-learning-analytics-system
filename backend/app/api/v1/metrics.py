from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import Role, User
from app.schemas.common import Page
from app.schemas.metrics import ComputeRequest, ComputeResponse, MetricResultOut
from app.services import metric_engine
from app.services.pagination import PageParams, page_params

router = APIRouter(prefix="/metrics", tags=["metrics"])
staff = require_roles(Role.ADMIN, Role.REVIEWER)


@router.post("/compute", response_model=ComputeResponse, status_code=status.HTTP_201_CREATED)
def compute(body: ComputeRequest, user: User = Depends(staff), db: Session = Depends(get_db)):
    return metric_engine.compute(db, user, body.metric_definition_id)


@router.get("/results", response_model=Page[MetricResultOut])
def list_results(
    learner_id: str | None = None,
    metric_definition_id: int | None = None,
    flagged: bool | None = None,
    params: PageParams = Depends(page_params),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = metric_engine.list_results(db, user, params, learner_id, metric_definition_id, flagged)
    return Page(items=items, total=total, page=params.page, size=params.size)
