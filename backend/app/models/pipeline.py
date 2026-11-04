"""Ba bảng do pipeline (thư mục pipeline/) tạo và nạp vào PostgreSQL.

Backend chỉ ĐỌC các bảng này và không bao giờ tạo hoặc sửa chúng: pipeline mới là nơi định nghĩa
ràng buộc (NOT NULL, CHECK...). Cờ info["pipeline"] giúp init_db bỏ qua chúng khi tạo bảng.
Tên bảng và cột phải khớp pipeline/sql/schemas/*.sql.
"""

from sqlalchemy import ForeignKey, Numeric, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import AcademicStatus, str_enum

_PIPELINE = {"info": {"pipeline": True}}


class Program(Base):
    __tablename__ = "programs"
    __table_args__ = _PIPELINE

    program_id: Mapped[str] = mapped_column(Text, primary_key=True)
    program_name_vi: Mapped[str] = mapped_column(Text)
    program_name_en: Mapped[str] = mapped_column(Text)
    major_code: Mapped[str] = mapped_column(Text)
    program_type: Mapped[str] = mapped_column(Text)  # Standard, EP, POHE, CLC, TT
    first_cohort_year: Mapped[int] = mapped_column(SmallInteger)
    last_cohort_year: Mapped[int] = mapped_column(SmallInteger)


class Student(Base):
    __tablename__ = "students"
    __table_args__ = _PIPELINE

    student_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    program_id: Mapped[str] = mapped_column(ForeignKey("programs.program_id"))
    cohort: Mapped[int] = mapped_column(SmallInteger)
    academic_status: Mapped[AcademicStatus] = mapped_column(str_enum(AcademicStatus))


class AcademicPerformance(Base):
    __tablename__ = "academic_performance"
    __table_args__ = _PIPELINE

    student_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), primary_key=True)
    academic_year: Mapped[str] = mapped_column(Text, primary_key=True)  # "2025-2026"
    semester: Mapped[int] = mapped_column(SmallInteger, primary_key=True)  # 1 hoặc 2
    registered_credits: Mapped[int] = mapped_column(SmallInteger)
    passed_credits: Mapped[int] = mapped_column(SmallInteger)
    failed_credits: Mapped[int] = mapped_column(SmallInteger)
    semester_gpa: Mapped[float] = mapped_column(Numeric(3, 2, asdecimal=False))  # thang 4
    cumulative_gpa: Mapped[float] = mapped_column(Numeric(3, 2, asdecimal=False))
