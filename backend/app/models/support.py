from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import AlertStatus, CaseStatus, ResultStatus, str_enum
from app.models.metric import MetricResult
from app.models.pipeline import Student


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_result_id: Mapped[int] = mapped_column(ForeignKey("metric_results.id"), unique=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), index=True)  # mã sinh viên
    status: Mapped[AlertStatus] = mapped_column(str_enum(AlertStatus), default=AlertStatus.PENDING_REVIEW)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    review_note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)

    metric_result: Mapped[MetricResult] = relationship()
    learner: Mapped[Student] = relationship()
    support_case: Mapped["SupportCase | None"] = relationship(back_populates="alert", uselist=False)


class SupportCase(Base):
    __tablename__ = "support_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), unique=True)
    learner_id: Mapped[str] = mapped_column(ForeignKey("students.student_id"), index=True)  # mã sinh viên
    status: Mapped[CaseStatus] = mapped_column(str_enum(CaseStatus), default=CaseStatus.OPEN)
    reason: Mapped[str] = mapped_column(String(1000))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    alert: Mapped[Alert] = relationship(back_populates="support_case")
    learner: Mapped[Student] = relationship()
    followups: Mapped[list["Followup"]] = relationship(back_populates="case", order_by="Followup.id")


class Followup(Base):
    __tablename__ = "followups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("support_cases.id"), index=True)
    action: Mapped[str] = mapped_column(String(1000))
    outcome: Mapped[str | None] = mapped_column(String(1000))
    result_status: Mapped[ResultStatus] = mapped_column(str_enum(ResultStatus), default=ResultStatus.UNKNOWN)
    post_metric_result_id: Mapped[int | None] = mapped_column(ForeignKey("metric_results.id"))
    performed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    performed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    case: Mapped[SupportCase] = relationship(back_populates="followups")
    post_metric_result: Mapped[MetricResult | None] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
