"""Tính chỉ số học tập từ bảng academic_performance (do pipeline nạp, chỉ gồm dòng đã kiểm tra).

QUY TẮC CỨNG: chỉ tính bằng công thức đã approved (ngược lại 409).
Kết quả vượt ngưỡng chỉ tạo Alert ở trạng thái pending_review; mọi quyết định tiếp theo
phải do giáo viên xác nhận ở bước rà soát.

Chỉ tính cho sinh viên đang học (studying): học kỳ gần nhất và các học kỳ đã từng có kết quả.
Nguồn thay đổi tạo revision mới; nguồn không đổi được bỏ qua. Giữ lịch sử kết quả và case.
"""

import operator
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.permissions import ensure_learner_access, get_learner_or_404, scope_by_learner
from app.models import (
    AcademicPerformance,
    AcademicStatus,
    Alert,
    AlertStatus,
    FormulaType,
    MetricDefinition,
    MetricResult,
    MetricStatus,
    Student,
    User,
)
from app.services.pagination import PageParams
from app.services import audit_service

OPERATORS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge, "==": operator.eq}


@dataclass
class Term:
    academic_year: str
    semester: int
    registered_credits: float
    failed_credits: float
    cumulative_gpa: float


# --- Công thức (terms: các học kỳ của một sinh viên, mới nhất trước) ---------------------------

def cumulative_gpa(terms: list[Term], params: dict) -> float:
    return terms[0].cumulative_gpa


def failed_credit_ratio(terms: list[Term], params: dict) -> float | None:
    recent = terms[:params.get("terms", 1)]
    registered = sum(t.registered_credits for t in recent)
    if registered <= 0:
        return None
    return round(sum(t.failed_credits for t in recent) / registered, 4)


FORMULAS = {
    FormulaType.CUMULATIVE_GPA: cumulative_gpa,
    FormulaType.FAILED_CREDIT_RATIO: failed_credit_ratio,
}


def is_flagged(value: float | None, threshold: dict) -> bool:
    """Vượt ngưỡng khi `value <operator> threshold.value` đúng. Không có giá trị thì không cảnh báo."""
    if value is None:
        return False
    return OPERATORS[threshold["operator"]](value, float(threshold["value"]))


# --- Tính và lưu kết quả ---------------------------------------------------------------

def _load_terms(db: Session) -> dict[str, list[Term]]:
    """Kết quả học kỳ của sinh viên đang học, theo từng sinh viên, học kỳ mới nhất trước."""
    by_student: dict[str, list[Term]] = defaultdict(list)
    rows = db.execute(
        select(AcademicPerformance.student_id, AcademicPerformance.academic_year, AcademicPerformance.semester,
               AcademicPerformance.registered_credits, AcademicPerformance.failed_credits,
               AcademicPerformance.cumulative_gpa)
        .join(Student, Student.student_id == AcademicPerformance.student_id)
        .where(Student.academic_status == AcademicStatus.STUDYING)
        .order_by(AcademicPerformance.student_id, AcademicPerformance.academic_year.desc(),
                  AcademicPerformance.semester.desc())
    )
    for student_id, *fields in rows:
        by_student[student_id].append(Term(*fields))
    return by_student


def _approved_definition(db: Session, definition_id: int) -> MetricDefinition:
    definition = db.scalar(select(MetricDefinition).where(MetricDefinition.id == definition_id)
                           .with_for_update().execution_options(populate_existing=True))
    if definition is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy công thức chỉ số")
    if definition.status != MetricStatus.APPROVED:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Công thức chưa được phê duyệt, không thể tính")
    return definition


def _source_hash(definition: MetricDefinition, terms: list[Term]) -> str:
    if definition.formula_type == FormulaType.CUMULATIVE_GPA:
        source = [[terms[0].academic_year, terms[0].semester, float(terms[0].cumulative_gpa)]]
    else:
        source = [[t.academic_year, t.semester, float(t.registered_credits), float(t.failed_credits)]
                  for t in terms[:definition.formula_params.get("terms", 1)]]
    return hashlib.sha256(json.dumps(source, separators=(",", ":")).encode()).hexdigest()


def compute(db: Session, user: User, definition_id: int, now: datetime | None = None) -> dict:
    definition = _approved_definition(db, definition_id)
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    formula = FORMULAS[FormulaType(definition.formula_type)]

    terms_by_student = _load_terms(db)
    if not terms_by_student:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            detail="Chưa có dữ liệu học tập của sinh viên đang học để tính")

    done = {}
    for result in db.scalars(select(MetricResult)
                            .where(MetricResult.metric_definition_id == definition.id)
                            .order_by(MetricResult.revision)):
        done[(result.learner_id, result.academic_year, result.semester)] = result

    results: list[MetricResult] = []
    skipped = 0
    changed_students = set()
    superseded_ids = []
    for student_id, terms in sorted(terms_by_student.items()):
        for index, term in enumerate(terms):
            previous = done.get((student_id, term.academic_year, term.semester))
            # Tính học kỳ mới nhất và kiểm tra lại các học kỳ đã từng có kết quả.
            if index != 0 and previous is None:
                continue
            source_hash = _source_hash(definition, terms[index:])
            if previous is not None and previous.source_hash == source_hash:
                continue
            value = formula(terms[index:], definition.formula_params)
            results.append(MetricResult(
                metric_definition_id=definition.id, learner_id=student_id, academic_year=term.academic_year,
                semester=term.semester, value=value, flagged=is_flagged(value, definition.threshold),
                computed_at=now, revision=previous.revision + 1 if previous else 1, source_hash=source_hash,
            ))
            changed_students.add(student_id)
            if previous is not None:
                superseded_ids.append(previous.id)
        if student_id not in changed_students:
            skipped += 1
    if not results:
        # Tránh sinh cảnh báo trùng cho giáo viên rà soát.
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Chỉ số này đã được tính trên dữ liệu hiện có")

    try:
        # Chỉ kết thúc cảnh báo chưa rà soát; giữ nguyên quyết định của giáo viên và case.
        if superseded_ids:
            note = "Hệ thống: dữ liệu nguồn đã thay đổi; xem kết quả tính lại."
            dismissed = db.scalars(update(Alert).where(Alert.metric_result_id.in_(superseded_ids),
                                           Alert.status == AlertStatus.PENDING_REVIEW)
                       .values(status=AlertStatus.DISMISSED, reviewed_at=now,
                               review_note=note).returning(Alert.id)).all()
            for alert_id in dismissed:
                audit_service.record(db, user, audit_service.ALERT_DISMISS, audit_service.ALERT,
                                     alert_id, {"note": note, "automatic": True,
                                                "reason": "source_data_changed"})
        db.add_all(results)
        db.flush()  # cần id của MetricResult để gắn Alert

        alerts = [Alert(metric_result_id=r.id, learner_id=r.learner_id, status=AlertStatus.PENDING_REVIEW,
                        created_at=now)
                  for r in results if r.flagged]
        db.add_all(alerts)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "metric_definition_id": definition.id,
        "metric_code": definition.code,
        "metric_version": definition.version,
        "computed_at": now,
        "learners_computed": len(changed_students),
        "learners_skipped": skipped,
        "flagged": sum(1 for r in results if r.flagged),
        "alerts_created": len(alerts),
    }


# --- Tra cứu kết quả (lọc theo phạm vi nhóm) -------------------------------------------

def result_to_dict(result: MetricResult, student_name: str | None, definition: MetricDefinition) -> dict:
    return {
        "id": result.id,
        "learner_id": result.learner_id,
        "learner_name": student_name,
        "metric_definition_id": definition.id,
        "metric_code": definition.code,
        "metric_version": definition.version,
        "academic_year": result.academic_year,
        "semester": result.semester,
        "value": result.value,
        "flagged": result.flagged,
        "threshold": definition.threshold,
        "computed_at": result.computed_at,
    }


def list_results(db: Session, user: User, params: PageParams, learner_id: str | None,
                 metric_definition_id: int | None, flagged: bool | None) -> tuple[list[dict], int]:
    if learner_id is not None:
        get_learner_or_404(db, learner_id)
        ensure_learner_access(db, user, learner_id)

    stmt = (select(MetricResult, Student.name, MetricDefinition)
            .join(Student, Student.student_id == MetricResult.learner_id)
            .join(MetricDefinition, MetricDefinition.id == MetricResult.metric_definition_id)
            .order_by(MetricResult.computed_at.desc(), MetricResult.id.desc()))
    stmt = scope_by_learner(stmt, MetricResult.learner_id, user)
    if learner_id is not None:
        stmt = stmt.where(MetricResult.learner_id == learner_id)
    if metric_definition_id is not None:
        stmt = stmt.where(MetricResult.metric_definition_id == metric_definition_id)
    if flagged is not None:
        stmt = stmt.where(MetricResult.flagged.is_(flagged))

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(stmt.offset(params.offset).limit(params.size)).all()
    return [result_to_dict(r, name, d) for r, name, d in rows], total
