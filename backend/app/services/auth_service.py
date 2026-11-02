from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import accessible_group_ids
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.auth import LoginResponse, MeResponse, UserBrief


def login(db: Session, email: str, password: str) -> LoginResponse:
    user = db.scalars(select(User).where(func.lower(User.email) == email.strip().lower())).first()
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Tài khoản đã bị khoá")
    return LoginResponse(
        access_token=create_access_token(user.id, user.role.value),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserBrief.model_validate(user),
    )


def me(db: Session, user: User) -> MeResponse:
    return MeResponse(
        id=user.id, email=user.email, full_name=user.full_name, role=user.role,
        is_active=user.is_active, group_ids=accessible_group_ids(db, user),
    )
