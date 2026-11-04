from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import Role, str_enum
from app.models.pipeline import Program

user_group_access = Table(
    "user_group_access",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("group_id", ForeignKey("learner_groups.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("student_id", name="uq_users_student_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), default=lambda ctx: ctx.get_current_parameters()["email"].strip().lower())
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    source_account_id: Mapped[str | None] = mapped_column(String(36), unique=True)
    staff_id: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(str_enum(Role))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    student_id: Mapped[str | None] = mapped_column(ForeignKey("students.student_id"))

    groups: Mapped[list["LearnerGroup"]] = relationship(secondary=user_group_access, back_populates="users")


Index("uq_users_username_ci", func.lower(User.username), unique=True)


class LearnerGroup(Base):
    """Nhóm phân quyền = một chương trình × một khoá (vd "EP03-2022").

    Không có bảng thành viên: sinh viên thuộc nhóm khi cùng program_id và cohort.
    Nhóm được tạo tự động từ bảng students (xem group_service).
    """

    __tablename__ = "learner_groups"
    __table_args__ = (UniqueConstraint("program_id", "cohort", name="uq_group_program_cohort"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    program_id: Mapped[str] = mapped_column(ForeignKey("programs.program_id"))
    cohort: Mapped[int] = mapped_column(Integer)

    program: Mapped[Program] = relationship()
    users: Mapped[list[User]] = relationship(secondary=user_group_access, back_populates="groups")
