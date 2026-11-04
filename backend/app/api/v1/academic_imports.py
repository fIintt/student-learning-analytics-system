from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.permissions import require_roles
from app.db.session import get_db
from app.models import Role, User
from app.schemas.academic_import import AcademicImportDetail, AcademicImportErrorOut, AcademicImportOut
from app.schemas.common import Page
from app.services import academic_import_service as service
from app.services.pagination import PageParams, page_params

router = APIRouter(prefix="/academic-imports", tags=["academic-imports"])
staff = require_roles(Role.ADMIN, Role.REVIEWER)


@router.get("/template")
def template(_user: User = Depends(staff)):
    content = ("\ufeffstudent_id,academic_year,semester,registered_credits,passed_credits,failed_credits,semester_gpa,cumulative_gpa\r\n"
               "11224850,2026-2027,1,20,18,2,3.10,2.85\r\n")
    return Response(content=content.encode("utf-8"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="academic-performance-template.csv"'})


@router.post("", response_model=AcademicImportOut, status_code=202)
def upload(tasks: BackgroundTasks, file: UploadFile = File(...), user: User = Depends(staff), db: Session = Depends(get_db)):
    job = service.create(db, user, file)
    tasks.add_task(service.run_job, db.get_bind(), job.id, "preview")
    return AcademicImportOut.model_validate(job)


@router.get("", response_model=Page[AcademicImportOut])
def list_imports(status: Literal["processing", "ready", "importing", "completed", "failed"] | None = Query(None),
                 params: PageParams = Depends(page_params), user: User = Depends(staff), db: Session = Depends(get_db)):
    rows, total = service.list_imports(db, user, params, status)
    return Page(items=[AcademicImportOut.model_validate(row) for row in rows], total=total,
                page=params.page, size=params.size)


@router.get("/{import_id}", response_model=AcademicImportDetail)
def get_import(import_id: int, user: User = Depends(staff), db: Session = Depends(get_db)):
    return service.get_detail(db, user, import_id)


@router.get("/{import_id}/errors", response_model=Page[AcademicImportErrorOut])
def errors(import_id: int, params: PageParams = Depends(page_params),
           user: User = Depends(staff), db: Session = Depends(get_db)):
    rows, total = service.errors(db, user, import_id, params)
    return Page(items=[AcademicImportErrorOut.model_validate(row) for row in rows], total=total,
                page=params.page, size=params.size)


@router.post("/{import_id}/confirm", response_model=AcademicImportOut, status_code=202)
def confirm(import_id: int, tasks: BackgroundTasks, user: User = Depends(staff), db: Session = Depends(get_db)):
    job, start = service.confirm(db, user, import_id)
    if start:
        tasks.add_task(service.run_job, db.get_bind(), job.id, "confirm")
    return AcademicImportOut.model_validate(job)
