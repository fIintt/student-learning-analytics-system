from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import MetricStatus, str_enum


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_metric_code_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(255))
    purpose: Mapped[str] = mapped_column(String(500), default="")
    formula_type: Mapped[str] = mapped_column(String(50))
    formula_params: Mapped[dict] = mapped_column(JSON, default=dict)
    threshold: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[MetricStatus] = mapped_column(str_enum(MetricStatus), default=MetricStatus.DRAFT)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)


class MetricResult(Base):
    """Kết quả một chỉ số của một sinh viên, tính trên học kỳ gần nhất (academic_year + semester).

    Truy vết: công thức + phiên bản (metric_definition_id), học kỳ nguồn trong academic_performance,
    thời điểm tính. Mỗi lần dữ liệu nguồn thay đổi tạo một revision, giữ nguyên kết quả cũ.
    """

    __tablename__ = "metric_results"
    __table_args__ = (UniqueConstraint("metric_definition_id", "learner_id", "academic_year", "semester", "revision",
                                       name="uq_metric_result_term_revision"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_definition_id: Mapped[int] = mapped_column(ForeignKey("metric_definitions.id"), index=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), index=True)  # mã sinh viên
    academic_year: Mapped[str] = mapped_column(Text)
    semester: Mapped[int] = mapped_column(SmallInteger)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    source_hash: Mapped[str | None] = mapped_column(String(64))
    value: Mapped[float | None] = mapped_column(Float)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    metric_definition: Mapped[MetricDefinition] = relationship()
