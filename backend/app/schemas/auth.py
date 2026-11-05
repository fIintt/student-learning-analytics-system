from pydantic import AliasChoices, BaseModel, Field, StringConstraints

from typing import Annotated

from app.models import Role
from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)] = Field(validation_alias=AliasChoices("username", "email"))
    password: str = Field(min_length=1, max_length=255)


class UserBrief(ORMModel):
    id: int
    username: str
    email: str | None
    full_name: str
    role: Role


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserBrief


class MeResponse(UserBrief):
    must_change_password: bool = False
    student_id: str | None = None
    is_active: bool
    group_ids: list[int]


class StudentLinkRequest(BaseModel):
    student_id: str | None = Field(min_length=1, max_length=255)


class AccountSyncItem(BaseModel):
    username: str
    status: str
    reason: str | None
    user_id: int | None


class AccountSyncResult(BaseModel):
    total: int
    created: int
    skipped: int
    conflicts: int
    items: list[AccountSyncItem]
