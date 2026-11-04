from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from app.core.permissions import require_roles
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import Role, Student, User
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse, StudentLinkRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login(db, body.username, body.password)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return auth_service.me(db, user)


@router.put("/users/{user_id}/student-link", response_model=MeResponse)
def link_student(user_id: int, body: StudentLinkRequest,
                 _admin: User = Depends(require_roles(Role.ADMIN)), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, detail="Không tìm thấy tài khoản")
    if user.role != Role.VIEWER:
        raise HTTPException(400, detail="Chỉ liên kết mã sinh viên cho tài khoản Sinh viên")
    if body.student_id is not None and db.get(Student, body.student_id) is None:
        raise HTTPException(404, detail="Không tìm thấy sinh viên")
    user.student_id = body.student_id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, detail="Mã sinh viên đã được liên kết với tài khoản khác")
    return auth_service.me(db, user)
