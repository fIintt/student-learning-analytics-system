from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.permissions import require_roles
from app.core.security import get_current_user, hash_password, verify_password
from app.db.session import get_db
from app.models import User, Role, Student, Program, AcademicPerformance, Alert, CaseStatus, MetricResult
from app.schemas.auth import MeResponse, AccountSyncResult
from app.services.account_sync_service import sync_accounts
from app.schemas.common import Page
from app.schemas.student_portal import (StudentAccountCreate, NewPassword, ChangePassword, AccountStatus,
    TermOut, TrendPoint, AcademicSummary, StudentProfile, StudentAlert)
from app.services.auth_service import me
from app.services.pagination import PageParams, page_params, paginate

router = APIRouter(tags=["student-portal"])
admin = require_roles(Role.ADMIN)


def own_student(user: User = Depends(require_roles(Role.VIEWER)), db: Session = Depends(get_db)):
    student = db.get(Student, user.student_id) if user.student_id else None
    if student is None:
        raise HTTPException(403, detail="Tài khoản chưa liên kết mã sinh viên, vui lòng liên hệ admin")
    return student


def student_account(db, user_id):
    user = db.get(User, user_id)
    if user is None or user.role != Role.VIEWER:
        raise HTTPException(404, detail="Không tìm thấy tài khoản Sinh viên")
    return user


@router.post("/admin/student-accounts", response_model=MeResponse, status_code=201)
def create_account(body: StudentAccountCreate, _admin: User = Depends(admin), db: Session = Depends(get_db)):
    student = db.get(Student, body.student_id)
    if student is None:
        raise HTTPException(404, detail="Không tìm thấy mã sinh viên trong pipeline")
    if db.scalar(select(User.id).where(func.lower(User.username) == body.username)):
        raise HTTPException(409, detail="Tên đăng nhập đã tồn tại")
    if body.email and db.scalar(select(User.id).where(func.lower(User.email) == body.email)):
        raise HTTPException(409, detail="Email đã tồn tại")
    user = User(username=body.username, email=body.email, full_name=student.name, role=Role.VIEWER, student_id=student.student_id,
                hashed_password=hash_password(body.password), must_change_password=True)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail="Tên đăng nhập, email hoặc mã sinh viên đã có tài khoản")
    return me(db, user)


@router.get("/admin/student-accounts", response_model=Page[MeResponse])
def accounts(params: PageParams = Depends(page_params), _admin: User = Depends(admin), db: Session = Depends(get_db)):
    rows, total = paginate(db, select(User).where(User.role == Role.VIEWER).order_by(User.id), params)
    return Page(items=[me(db, u) for u in rows], total=total, page=params.page, size=params.size)


@router.patch("/admin/student-accounts/{user_id}", response_model=MeResponse)
def account_status(user_id: int, body: AccountStatus, _admin: User = Depends(admin), db: Session = Depends(get_db)):
    user = student_account(db, user_id)
    user.is_active = body.is_active
    user.token_version += 1
    db.commit()
    return me(db, user)


@router.post("/admin/student-accounts/{user_id}/reset-password")
def reset_password(user_id: int, body: NewPassword, _admin: User = Depends(admin), db: Session = Depends(get_db)):
    user = student_account(db, user_id)
    user.hashed_password = hash_password(body.password)
    user.must_change_password = True
    user.token_version += 1
    db.commit()
    return {"detail": "Đã đặt mật khẩu tạm; sinh viên phải đăng nhập lại và đổi mật khẩu"}


@router.post("/auth/change-password")
def change_password(body: ChangePassword, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(400, detail="Mật khẩu hiện tại không đúng")
    if verify_password(body.password, user.hashed_password):
        raise HTTPException(400, detail="Mật khẩu mới phải khác mật khẩu hiện tại")
    user.hashed_password = hash_password(body.password)
    user.must_change_password = False
    user.token_version += 1
    db.commit()
    return {"detail": "Đã đổi mật khẩu, vui lòng đăng nhập lại"}


@router.get("/me/student-profile", response_model=StudentProfile)
def profile(student: Student = Depends(own_student), db: Session = Depends(get_db)):
    program = db.get(Program, student.program_id)
    return dict(student_id=student.student_id, name=student.name, program_id=student.program_id,
                program_name=program.program_name_vi if program else None, cohort=student.cohort,
                academic_status=student.academic_status)


def term_query(student_id, academic_year, semester):
    stmt = select(AcademicPerformance).where(AcademicPerformance.student_id == student_id)
    if academic_year is not None:
        stmt = stmt.where(AcademicPerformance.academic_year == academic_year)
    if semester is not None:
        stmt = stmt.where(AcademicPerformance.semester == semester)
    return stmt.order_by(AcademicPerformance.academic_year, AcademicPerformance.semester)


@router.get("/me/academic-performance", response_model=Page[TermOut])
def performance(academic_year: str | None = Query(None, pattern=r"^\d{4}-\d{4}$"),
                semester: int | None = Query(None, ge=1, le=2), params: PageParams = Depends(page_params),
                student: Student = Depends(own_student), db: Session = Depends(get_db)):
    rows, total = paginate(db, term_query(student.student_id, academic_year, semester), params)
    return Page(items=[TermOut.model_validate(r) for r in rows], total=total, page=params.page, size=params.size)


@router.get("/me/academic-summary", response_model=AcademicSummary)
def summary(student: Student = Depends(own_student), db: Session = Depends(get_db)):
    rows = db.scalars(term_query(student.student_id, None, None)).all()
    trend = []
    previous = None
    for row in rows:
        point = TrendPoint(**TermOut.model_validate(row).model_dump(),
            gpa_change=round(row.semester_gpa - previous, 2) if previous is not None else None,
            passed_percent=round(row.passed_credits / row.registered_credits * 100, 2) if row.registered_credits else None,
            failed_percent=round(row.failed_credits / row.registered_credits * 100, 2) if row.registered_credits else None)
        trend.append(point)
        previous = row.semester_gpa
    return AcademicSummary(term_count=len(rows), latest=trend[-1] if trend else None, trend=trend,
        highest_semester_gpa=max((r.semester_gpa for r in rows), default=None),
        lowest_semester_gpa=min((r.semester_gpa for r in rows), default=None))


def _support_message(case, advisor_name):
    """Dòng thông báo cho sinh viên; không lộ lý do nội bộ (reason) của case."""
    if case is None:
        return None
    if case.status == CaseStatus.CLOSED:
        return "Trường hợp hỗ trợ của bạn đã kết thúc."
    if advisor_name:
        return f"Cố vấn học tập {advisor_name} sẽ liên hệ với bạn."
    return "Cố vấn học tập sẽ liên hệ với bạn."


def personal_alert(db, alert):
    result = alert.metric_result
    definition = result.metric_definition
    case = alert.support_case
    advisor = db.get(User, case.assigned_to) if case and case.assigned_to else None
    advisor_name = advisor.full_name if advisor else None
    return StudentAlert(id=alert.id, status=alert.status, academic_year=result.academic_year,
        semester=result.semester, metric_code=definition.code, metric_name=definition.name,
        value=result.value, threshold=definition.threshold, created_at=alert.created_at,
        support_status=case.status.value if case else None, advisor_name=advisor_name,
        support_message=_support_message(case, advisor_name))


@router.get("/me/alerts", response_model=Page[StudentAlert])
def alerts(params: PageParams = Depends(page_params), student: Student = Depends(own_student), db: Session = Depends(get_db)):
    rows, total = paginate(db, select(Alert).where(Alert.learner_id == student.student_id)
                          .order_by(Alert.created_at.desc(), Alert.id.desc()), params)
    return Page(items=[personal_alert(db, a) for a in rows], total=total, page=params.page, size=params.size)


@router.get("/me/alerts/{alert_id}", response_model=StudentAlert)
def alert_detail(alert_id: int, student: Student = Depends(own_student), db: Session = Depends(get_db)):
    alert = db.scalar(select(Alert).where(Alert.id == alert_id, Alert.learner_id == student.student_id))
    if alert is None:
        raise HTTPException(404, detail="Không tìm thấy cảnh báo của bạn")
    return personal_alert(db, alert)


@router.post("/admin/accounts/sync", response_model=AccountSyncResult)
def sync_pipeline_accounts(_admin: User = Depends(admin), db: Session = Depends(get_db)):
    return sync_accounts(db)
