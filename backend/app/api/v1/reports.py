from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.reports import AggregateReport, LearnerReport
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/learner/{learner_id}", response_model=LearnerReport)
def learner_report(learner_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return report_service.learner_report(db, user, learner_id)


@router.get("/group/{group_id}", response_model=AggregateReport)
def group_report(group_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return report_service.group_report(db, user, group_id)


@router.get("/program/{program_id}", response_model=AggregateReport)
def program_report(program_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return report_service.program_report(db, user, program_id)
