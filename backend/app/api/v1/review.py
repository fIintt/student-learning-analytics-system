from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import AlertStatus, Role, User
from app.schemas.common import Page
from app.schemas.support import AlertOut, ConfirmRequest, ConfirmResponse, DismissRequest
from app.services import case_service, review_service
from app.services.pagination import PageParams, page_params

router = APIRouter(prefix="/review", tags=["review"])
staff = require_roles(Role.ADMIN, Role.REVIEWER)


@router.get("/alerts", response_model=Page[AlertOut])
def list_alerts(
    status_filter: AlertStatus | None = Query(None, alias="status"),
    learner_id: str | None = None,
    metric_definition_id: int | None = None,
    params: PageParams = Depends(page_params),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = review_service.list_alerts(db, user, params, status_filter, learner_id, metric_definition_id)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.get("/alerts/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return review_service.alert_to_dict(review_service.get_alert_for_user(db, user, alert_id))


@router.post("/alerts/{alert_id}/confirm", response_model=ConfirmResponse, status_code=status.HTTP_201_CREATED)
def confirm_alert(alert_id: int, body: ConfirmRequest = Body(default_factory=ConfirmRequest),
                  user: User = Depends(staff), db: Session = Depends(get_db)):
    alert, case = review_service.confirm(db, user, alert_id, body)
    return {"alert": review_service.alert_to_dict(alert), "support_case": case_service.case_to_dict(case)}


@router.post("/alerts/{alert_id}/dismiss", response_model=AlertOut)
def dismiss_alert(alert_id: int, body: DismissRequest = Body(default_factory=DismissRequest),
                  user: User = Depends(staff), db: Session = Depends(get_db)):
    return review_service.alert_to_dict(review_service.dismiss(db, user, alert_id, body))
