from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.core.security import get_current_user
from app.db.session import get_db
from app.models import Role, User
from app.schemas.common import Page
from app.schemas.support import FollowupCreate, FollowupOut
from app.services import followup_service
from app.services.pagination import PageParams, page_params

router = APIRouter(prefix="/followups", tags=["followups"])
staff = require_roles(Role.ADMIN, Role.REVIEWER)


@router.get("", response_model=Page[FollowupOut])
def list_followups(case_id: int | None = None, params: PageParams = Depends(page_params),
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items, total = followup_service.list_followups(db, user, params, case_id)
    return Page(items=items, total=total, page=params.page, size=params.size)


@router.post("", response_model=FollowupOut, status_code=status.HTTP_201_CREATED)
def create_followup(body: FollowupCreate, user: User = Depends(staff), db: Session = Depends(get_db)):
    return followup_service.create_followup(db, user, body)
