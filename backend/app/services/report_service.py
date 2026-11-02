"""Báo cáo theo người học, nhóm, chương trình. Luôn áp phạm vi nhóm của người xem."""

from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.permissions import (
    ensure_group_access,
    ensure_learner_access,
    get_learner_or_404,
    has_full_access,
    scope_by_learner,
)
from app.models import (
    Alert,
    AlertStatus,
    CaseStatus,
    Followup,
    LearnerGroup,
    MetricDefinition,
    MetricResult,
    Program,
    ResultStatus,
    Student,
    SupportCase,
    User,
)

_OPEN_CASE = (CaseStatus.OPEN, CaseStatus.IN_PROGRESS)


# --- truy vấn dùng chung --------------------------------------------------------------

def _results_by_learner_and_code(db: Session, learner_ids: Select) -> dict[str, dict[str, list[dict]]]:
    """{mã sinh viên: {metric_code: [kết quả, mới nhất trước]}}"""
    rows = db.execute(
        select(MetricResult.learner_id, MetricResult.value, MetricResult.flagged, MetricResult.computed_at,
               MetricResult.academic_year, MetricResult.semester, MetricDefinition.code, MetricDefinition.version)
        .join(MetricDefinition, MetricDefinition.id == MetricResult.metric_definition_id)
        .where(MetricResult.learner_id.in_(learner_ids))
        .order_by(MetricResult.academic_year.desc(), MetricResult.semester.desc(),
                  MetricDefinition.version.desc(), MetricResult.revision.desc(), MetricResult.id.desc())
    )
    out: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for learner_id, value, flagged, computed_at, academic_year, semester, code, version in rows:
        out[learner_id][code].append({"value": value, "flagged": flagged, "computed_at": computed_at,
                                      "academic_year": academic_year, "semester": semester,
                                      "metric_version": version})
    return out


def _count_by(db: Session, column, learner_column, learner_ids: Select, enum_cls, *joins) -> dict[str, int]:
    counts = {e.value: 0 for e in enum_cls}
    stmt = select(column, func.count()).where(learner_column.in_(learner_ids)).group_by(column)
    for target, onclause in joins:
        stmt = stmt.join(target, onclause)
    for key, n in db.execute(stmt):
        counts[key.value] = n
    return counts


def program_brief(program: Program) -> dict:
    return {"id": program.program_id, "name": program.program_name_vi, "name_en": program.program_name_en,
            "program_type": program.program_type}


# --- báo cáo người học -------------------------------------------------------------------

def learner_report(db: Session, user: User, learner_id: str) -> dict:
    student = get_learner_or_404(db, learner_id)
    ensure_learner_access(db, user, learner_id)
    ids = select(Student.student_id).where(Student.student_id == learner_id)

    metrics = []
    for code, history in sorted(_results_by_learner_and_code(db, ids).get(learner_id, {}).items()):
        latest = history[0]
        metrics.append({
            "metric_code": code, "metric_version": latest["metric_version"],
            "latest_value": latest["value"], "flagged": latest["flagged"],
            "computed_at": latest["computed_at"],
            "academic_year": latest["academic_year"], "semester": latest["semester"],
            "history": [{k: h[k] for k in ("value", "computed_at", "academic_year", "semester", "metric_version")}
                        for h in history],
        })

    cases = db.scalars(select(SupportCase).options(selectinload(SupportCase.followups))
                       .where(SupportCase.learner_id == learner_id)
                       .order_by(SupportCase.created_at.desc(), SupportCase.id.desc())).all()
    program = db.get(Program, student.program_id)
    groups = db.scalars(select(LearnerGroup).where(LearnerGroup.program_id == student.program_id,
                                                   LearnerGroup.cohort == student.cohort)
                        .order_by(LearnerGroup.id)).all()

    return {
        "learner": {
            "id": student.student_id, "full_name": student.name,
            "program": program_brief(program) if program else None,
            "cohort": student.cohort,
            "academic_status": student.academic_status,
            "groups": [{"id": g.id, "name": g.name} for g in groups],
        },
        "metrics": metrics,
        "alerts": _count_by(db, Alert.status, Alert.learner_id, ids, AlertStatus),
        "support_cases": [{
            "id": c.id, "status": c.status, "reason": c.reason, "created_at": c.created_at,
            "followup_count": len(c.followups),
            "latest_result_status": c.followups[-1].result_status if c.followups else None,
        } for c in cases],
    }


# --- báo cáo tổng hợp (nhóm / chương trình) ------------------------------------------------

def _aggregate_report(db: Session, scope: dict, learner_ids: Select) -> dict:
    students = db.scalars(select(Student).where(Student.student_id.in_(learner_ids))
                          .order_by(Student.student_id)).all()
    results = _results_by_learner_and_code(db, learner_ids)

    # Mỗi sinh viên lấy kết quả mới nhất của từng chỉ số.
    per_code: dict[str, list[dict]] = defaultdict(list)
    flagged_codes: dict[str, list[str]] = defaultdict(list)
    for learner_id, by_code in results.items():
        for code, history in by_code.items():
            per_code[code].append(history[0])
            if history[0]["flagged"]:
                flagged_codes[learner_id].append(code)

    metrics = []
    for code, latest in sorted(per_code.items()):
        values = [r["value"] for r in latest if r["value"] is not None]
        flagged = sum(1 for r in latest if r["flagged"])
        newest = max(latest, key=lambda r: r["computed_at"])
        metrics.append({
            "metric_code": code, "metric_version": newest["metric_version"],
            "learners_with_result": len(latest),
            "avg_value": round(sum(values) / len(values), 2) if values else None,
            "min_value": min(values) if values else None,
            "max_value": max(values) if values else None,
            "flagged_count": flagged,
            "flagged_ratio": round(flagged / len(latest), 3) if latest else 0.0,
        })

    open_case_learners = set(db.scalars(select(SupportCase.learner_id).where(
        SupportCase.learner_id.in_(learner_ids), SupportCase.status.in_(_OPEN_CASE))))

    return {
        "scope": scope,
        "learner_count": len(students),
        "metrics": metrics,
        "alerts": _count_by(db, Alert.status, Alert.learner_id, learner_ids, AlertStatus),
        "support_cases": _count_by(db, SupportCase.status, SupportCase.learner_id, learner_ids, CaseStatus),
        "followups": _count_by(db, Followup.result_status, SupportCase.learner_id, learner_ids, ResultStatus,
                               (SupportCase, SupportCase.id == Followup.case_id)),
        "learners_needing_support": [{
            "id": s.student_id, "full_name": s.name,
            "flagged_metrics": sorted(flagged_codes.get(s.student_id, [])),
            "open_case": s.student_id in open_case_learners,
        } for s in students if flagged_codes.get(s.student_id) or s.student_id in open_case_learners],
    }


def group_report(db: Session, user: User, group_id: int) -> dict:
    group = db.get(LearnerGroup, group_id)
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhóm")
    ensure_group_access(db, user, group_id)
    learner_ids = select(Student.student_id).where(Student.program_id == group.program_id,
                                                   Student.cohort == group.cohort)
    return _aggregate_report(db, {"type": "group", "id": group.id, "name": group.name}, learner_ids)


def program_report(db: Session, user: User, program_id: str) -> dict:
    program = db.get(Program, program_id)
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chương trình")
    learner_ids = scope_by_learner(select(Student.student_id).where(Student.program_id == program_id),
                                   Student.student_id, user)
    if not has_full_access(user) and db.scalar(select(func.count()).select_from(learner_ids.subquery())) == 0:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền xem chương trình này")
    return _aggregate_report(db, {"type": "program", "id": program.program_id, "name": program.program_name_vi},
                             learner_ids)
