from pydantic import BaseModel, Field

from app.models import Role
from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=1, max_length=255)


class UserBrief(ORMModel):
    id: int
    email: str
    full_name: str
    role: Role


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserBrief


class MeResponse(UserBrief):
    is_active: bool
    group_ids: list[int]
