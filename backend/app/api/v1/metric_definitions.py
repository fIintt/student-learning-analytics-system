from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import MetricStatus, Role, User
from app.schemas.common import Page
from app.schemas.metric_definition import (
    ApproveRequest,
    MetricDefinitionCreate,
    MetricDefinitionOut,
    MetricDefinitionUpdate,
    RejectRequest,
)
from app.services import metric_definition_service as service
from app.services.pagination import PageParams, page_params

router = APIRouter(prefix="/metric-definitions", tags=["metric-definitions"])
staff = require_roles(Role.ADMIN, Role.REVIEWER)
admin_only = require_roles(Role.ADMIN)


@router.get("", response_model=Page[MetricDefinitionOut])
def list_definitions(
    status_filter: MetricStatus | None = Query(None, alias="status"),
    code: str | None = None,
    params: PageParams = Depends(page_params),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = service.list_definitions(db, params, status_filter, code)
    return Page(items=[MetricDefinitionOut.model_validate(d) for d in items], total=total,
                page=params.page, size=params.size)


@router.get("/{definition_id}", response_model=MetricDefinitionOut)
def get_definition(definition_id: int, _user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.get_or_404(db, definition_id)


@router.post("", response_model=MetricDefinitionOut, status_code=status.HTTP_201_CREATED)
def create_definition(body: MetricDefinitionCreate, user: User = Depends(staff), db: Session = Depends(get_db)):
    return service.create(db, user, body)


@router.patch("/{definition_id}", response_model=MetricDefinitionOut)
def update_definition(definition_id: int, body: MetricDefinitionUpdate,
                      _user: User = Depends(staff), db: Session = Depends(get_db)):
    return service.update(db, definition_id, body)


@router.post("/{definition_id}/submit", response_model=MetricDefinitionOut)
def submit_definition(definition_id: int, _user: User = Depends(staff), db: Session = Depends(get_db)):
    return service.submit(db, definition_id)


@router.post("/{definition_id}/approve", response_model=MetricDefinitionOut)
def approve_definition(definition_id: int, body: ApproveRequest | None = Body(None),
                       user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return service.approve(db, user, definition_id, body.note if body else None)


@router.post("/{definition_id}/reject", response_model=MetricDefinitionOut)
def reject_definition(definition_id: int, body: RejectRequest,
                      user: User = Depends(admin_only), db: Session = Depends(get_db)):
    return service.reject(db, user, definition_id, body.note)


@router.post("/{definition_id}/new-version", response_model=MetricDefinitionOut,
             status_code=status.HTTP_201_CREATED)
def new_version(definition_id: int, body: MetricDefinitionUpdate | None = Body(None),
                user: User = Depends(staff), db: Session = Depends(get_db)):
    return service.new_version(db, user, definition_id, body or MetricDefinitionUpdate())
