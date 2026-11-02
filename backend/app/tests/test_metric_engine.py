import pytest
from sqlalchemy import select

from app.models import AcademicPerformance, AcademicStatus, Alert, AlertStatus, AuditLog, MetricResult, MetricStatus, SupportCase
from app.services.metric_engine import is_flagged
from app.tests.conftest import add_term, make_definition

COMPUTE = "/api/v1/metrics/compute"
FAILED = dict(code="FAILED", formula_type="failed_credit_ratio", formula_params={"terms": 1},
              threshold={"operator": ">", "value": 0.25})


def _compute(client, auth, definition_id, role="reviewer"):
    return client.post(COMPUTE, json={"metric_definition_id": definition_id}, headers=auth[role])


def _results(db, definition_id) -> dict[str, MetricResult]:
    db.expire_all()
    rows = db.scalars(select(MetricResult).where(MetricResult.metric_definition_id == definition_id)
                      .order_by(MetricResult.id))
    return {r.learner_id: r for r in rows}


# --- QUY TẮC CỨNG: công thức chưa duyệt → 409 -------------------------------------------

@pytest.mark.parametrize("status", [MetricStatus.DRAFT, MetricStatus.PENDING, MetricStatus.REJECTED,
                                    MetricStatus.RETIRED])
def test_unapproved_definition_409(client, db, world, auth, status):
    add_term(db, "HS001", cumulative_gpa=1.0)
    definition = make_definition(db, world["admin"], status=status)
    res = _compute(client, auth, definition.id)
    assert res.status_code == 409
    assert res.json() == {"detail": "Công thức chưa được phê duyệt, không thể tính"}
    assert db.query(MetricResult).count() == 0
    assert db.query(Alert).count() == 0


def test_not_found_404_and_viewer_403(client, db, world, auth):
    add_term(db, "HS001")
    definition = make_definition(db, world["admin"])
    assert _compute(client, auth, 999).status_code == 404
    assert _compute(client, auth, definition.id, role="viewer").status_code == 403


def test_no_data_409(client, db, world, auth):
    definition = make_definition(db, world["admin"])
    res = _compute(client, auth, definition.id)
    assert res.status_code == 409
    assert res.json() == {"detail": "Chưa có dữ liệu học tập của sinh viên đang học để tính"}


# --- đã duyệt → MetricResult và Alert đúng ngưỡng -------------------------------------------

def test_cumulative_gpa_uses_latest_term(client, db, world, auth):
    hs1, hs2, hs3, _ = world["learners"]
    # HS001: kỳ mới nhất là 2025-2026 HK1 (1.8) dù các dòng thêm vào theo thứ tự khác → cảnh báo
    add_term(db, "HS001", "2024-2025", 2, cumulative_gpa=2.5)
    add_term(db, "HS001", "2025-2026", 1, cumulative_gpa=1.8)
    # HS002: kỳ mới nhất HK2 2024-2025 (2.4), kỳ cũ thấp hơn → không cảnh báo
    add_term(db, "HS002", "2024-2025", 1, cumulative_gpa=1.5)
    add_term(db, "HS002", "2024-2025", 2, cumulative_gpa=2.4)
    # HS003: đúng ngưỡng 2.0 → không cảnh báo (ngưỡng < 2.0)
    add_term(db, "HS003", cumulative_gpa=2.0)
    definition = make_definition(db, world["admin"])

    res = _compute(client, auth, definition.id)
    assert res.status_code == 201, res.text
    body = res.json()
    assert (body["metric_code"], body["metric_version"]) == ("CUM_GPA", 1)
    assert (body["learners_computed"], body["learners_skipped"], body["flagged"], body["alerts_created"]) == (3, 0, 1, 1)
    assert body["computed_at"].endswith("Z") and "batch_id" not in body

    results = _results(db, definition.id)
    assert {sid: (r.value, r.flagged, r.academic_year, r.semester) for sid, r in results.items()} == {
        "HS001": (1.8, True, "2025-2026", 1),
        "HS002": (2.4, False, "2024-2025", 2),
        "HS003": (2.0, False, "2025-2026", 1),
    }
    assert all(r.computed_at is not None for r in results.values())  # truy vết: công thức, học kỳ nguồn, thời điểm
    [alert] = db.scalars(select(Alert)).all()
    assert (alert.learner_id, alert.status, alert.metric_result_id) == (
        "HS001", AlertStatus.PENDING_REVIEW, results["HS001"].id)


def test_only_studying_students_are_computed(client, db, world, auth):
    hs1, hs2, hs3, hs4 = world["learners"]
    hs2.academic_status = AcademicStatus.GRADUATED
    hs3.academic_status = AcademicStatus.SUSPENDED
    db.commit()
    for learner in world["learners"]:
        add_term(db, learner.student_id, cumulative_gpa=1.0)
    definition = make_definition(db, world["admin"])
    body = _compute(client, auth, definition.id).json()
    assert (body["learners_computed"], body["alerts_created"]) == (2, 2)
    assert set(_results(db, definition.id)) == {"HS001", "HS004"}


def test_failed_credit_ratio(client, db, world, auth):
    add_term(db, "HS001", "2025-2026", 1, registered=21, failed=6)      # 6/21 = 0.2857 → cảnh báo
    add_term(db, "HS001", "2024-2025", 2, registered=18, failed=0)
    add_term(db, "HS002", "2025-2026", 1, registered=20, failed=5)      # 5/20 = 0.25 → không
    add_term(db, "HS002", "2024-2025", 2, registered=20, failed=10)
    add_term(db, "HS003", "2025-2026", 1, registered=0, failed=0)       # không đăng ký → không có giá trị
    one_term = make_definition(db, world["admin"], **FAILED)
    two_terms = make_definition(db, world["admin"], **{**FAILED, "code": "FAILED2", "formula_params": {"terms": 2}})
    _compute(client, auth, one_term.id)
    _compute(client, auth, two_terms.id)

    r1 = _results(db, one_term.id)
    assert (r1["HS001"].value, r1["HS001"].flagged) == (0.2857, True)
    assert (r1["HS002"].value, r1["HS002"].flagged) == (0.25, False)
    assert (r1["HS003"].value, r1["HS003"].flagged) == (None, False)
    r2 = _results(db, two_terms.id)
    assert (r2["HS001"].value, r2["HS001"].flagged) == (0.1538, False)   # 6 / 39
    assert (r2["HS002"].value, r2["HS002"].flagged) == (0.375, True)     # 15 / 40


# --- mỗi (công thức, sinh viên, học kỳ) chỉ tính một lần -----------------------------------------

def test_recompute_on_same_data_409_and_no_duplicate_alerts(client, db, world, auth):
    add_term(db, "HS001", cumulative_gpa=1.0)
    add_term(db, "HS002", cumulative_gpa=3.0)
    definition = make_definition(db, world["admin"])
    assert _compute(client, auth, definition.id).status_code == 201

    res = _compute(client, auth, definition.id, role="admin")
    assert res.status_code == 409
    assert res.json() == {"detail": "Chỉ số này đã được tính trên dữ liệu hiện có"}
    assert db.query(MetricResult).count() == 2 and db.query(Alert).count() == 1


def test_recompute_after_new_term_only_computes_new_data(client, db, world, auth):
    """Pipeline nạp thêm học kỳ mới → chỉ phần mới được tính, phần cũ được bỏ qua."""
    add_term(db, "HS001", "2025-2026", 1, cumulative_gpa=1.0)
    add_term(db, "HS002", "2025-2026", 1, cumulative_gpa=3.0)
    definition = make_definition(db, world["admin"])
    _compute(client, auth, definition.id)

    add_term(db, "HS001", "2025-2026", 2, cumulative_gpa=1.2)   # HS001 có học kỳ mới
    add_term(db, "HS003", "2025-2026", 1, cumulative_gpa=1.1)   # HS003 mới có dữ liệu
    body = _compute(client, auth, definition.id).json()
    assert (body["learners_computed"], body["learners_skipped"], body["alerts_created"]) == (2, 1, 2)

    db.expire_all()
    rows = db.scalars(select(MetricResult).where(MetricResult.learner_id == "HS001")
                      .order_by(MetricResult.id)).all()
    assert [(r.academic_year, r.semester, r.value) for r in rows] == [("2025-2026", 1, 1.0), ("2025-2026", 2, 1.2)]


@pytest.mark.parametrize("value,op,limit,expected", [
    (1.9, "<", 2, True), (2, "<", 2, False), (2, "<=", 2, True), (0.3, ">", 0.25, True),
    (0.25, ">", 0.25, False), (0.25, ">=", 0.25, True), (2, "==", 2, True), (None, "<", 2, False),
])
def test_threshold_operators(value, op, limit, expected):
    assert is_flagged(value, {"operator": op, "value": limit}) is expected


def test_old_version_stays_traceable(client, db, world, auth):
    add_term(db, "HS001", cumulative_gpa=1.8)
    v1 = make_definition(db, world["admin"], version=1)
    _compute(client, auth, v1.id)
    v1.status = MetricStatus.RETIRED
    v2 = make_definition(db, world["admin"], version=2, threshold={"operator": "<", "value": 1.5})
    db.commit()
    _compute(client, auth, v2.id)
    assert _compute(client, auth, v1.id).status_code == 409   # bản đã retired không tính được nữa

    res = client.get("/api/v1/metrics/results", headers=auth["admin"]).json()
    assert [(i["metric_version"], i["flagged"], i["academic_year"], i["semester"]) for i in res["items"]] == [
        (2, False, "2025-2026", 1), (1, True, "2025-2026", 1)]


# --- GET /metrics/results theo phạm vi nhóm ---------------------------------------------

def test_results_scoped_by_group(client, db, world, auth):
    for learner in world["learners"]:
        add_term(db, learner.student_id, cumulative_gpa=1.5)
    definition = make_definition(db, world["admin"])
    _compute(client, auth, definition.id)

    viewer = client.get("/api/v1/metrics/results", headers=auth["viewer"]).json()
    assert {i["learner_id"] for i in viewer["items"]} == {"HS001", "HS002"}
    assert set(viewer["items"][0]) == {"id", "learner_id", "learner_name", "metric_definition_id", "metric_code",
                                       "metric_version", "academic_year", "semester", "value", "flagged",
                                       "threshold", "computed_at"}
    assert viewer["items"][0]["learner_name"].startswith("Học sinh")
    assert client.get("/api/v1/metrics/results", headers=auth["admin"]).json()["total"] == 4
    assert client.get("/api/v1/metrics/results", params={"learner_id": "HS004"},
                      headers=auth["viewer"]).status_code == 403
    assert client.get("/api/v1/metrics/results", params={"learner_id": "KHONG-CO"},
                      headers=auth["viewer"]).status_code == 404


@pytest.mark.parametrize("old_gpa,new_gpa", [(1.5, 2.8), (2.8, 1.5), (1.5, 1.8)])
def test_source_correction_creates_revision_and_reconciles_alerts(client, db, world, auth, old_gpa, new_gpa):
    add_term(db, "HS001", cumulative_gpa=old_gpa)
    definition = make_definition(db, world["admin"])
    assert _compute(client, auth, definition.id).status_code == 201
    old_result = _results(db, definition.id)["HS001"]
    old_id = old_result.id
    term = db.get(AcademicPerformance, ("HS001", "2025-2026", 1))
    term.cumulative_gpa = new_gpa
    db.commit()

    response = _compute(client, auth, definition.id)
    assert response.status_code == 201, response.text
    assert response.json()["learners_computed"] == 1
    assert response.json()["alerts_created"] == int(new_gpa < 2)
    db.expire_all()
    rows = db.scalars(select(MetricResult).order_by(MetricResult.revision)).all()
    assert [(r.value, r.revision) for r in rows] == [(old_gpa, 1), (new_gpa, 2)]
    assert rows[0].id == old_id
    if old_gpa < 2:
        old_alert = db.scalar(select(Alert).where(Alert.metric_result_id == old_id))
        assert old_alert.status == AlertStatus.DISMISSED
        assert old_alert.reviewer_id is None
        assert "dữ liệu nguồn" in old_alert.review_note
        log = db.scalar(select(AuditLog).where(AuditLog.entity_id == old_alert.id,
                                               AuditLog.action == "alert.dismiss"))
        assert log.detail["automatic"] is True
    report = client.get("/api/v1/reports/learner/HS001", headers=auth["admin"]).json()
    assert report["metrics"][0]["latest_value"] == new_gpa
    assert len(report["metrics"][0]["history"]) == 2
    assert _compute(client, auth, definition.id).status_code == 409
    assert db.query(MetricResult).count() == 2


@pytest.mark.parametrize("new_gpa", [1.8, 2.8])
def test_correction_preserves_confirmed_case_and_followup(client, db, world, auth, new_gpa):
    add_term(db, "HS001", cumulative_gpa=1.5)
    definition = make_definition(db, world["admin"])
    _compute(client, auth, definition.id)
    old_result = _results(db, definition.id)["HS001"]
    alert = db.scalar(select(Alert))
    confirmed = client.post(f"/api/v1/review/alerts/{alert.id}/confirm",
                            json={"note": "Đã rà soát", "reason": "Cần hỗ trợ"}, headers=auth["admin"])
    assert confirmed.status_code == 201
    case_id = confirmed.json()["support_case"]["id"]
    followup = client.post("/api/v1/followups", headers=auth["admin"],
                           json={"case_id": case_id, "action": "Tư vấn", "post_metric_result_id": old_result.id})
    assert followup.status_code == 201
    db.get(AcademicPerformance, ("HS001", "2025-2026", 1)).cumulative_gpa = new_gpa
    db.commit()
    assert _compute(client, auth, definition.id).json()["alerts_created"] == int(new_gpa < 2)
    db.expire_all()
    assert db.get(Alert, alert.id).status == AlertStatus.CONFIRMED
    case = db.get(SupportCase, case_id)
    assert case.alert_id == alert.id
    assert case.followups[0].post_metric_result.value == 1.5
    assert db.query(SupportCase).count() == 1


def test_correcting_old_term_recomputes_multi_term_ratio(client, db, world, auth):
    add_term(db, "HS001", "2024-2025", 2, registered=20, failed=0)
    definition = make_definition(db, world["admin"], **{**FAILED, "formula_params": {"terms": 2}})
    _compute(client, auth, definition.id)
    add_term(db, "HS001", "2025-2026", 1, registered=20, failed=0)
    _compute(client, auth, definition.id)
    old_term = db.get(AcademicPerformance, ("HS001", "2024-2025", 2))
    old_term.failed_credits = 12
    old_term.passed_credits = 8
    db.commit()
    response = _compute(client, auth, definition.id)
    assert response.status_code == 201
    assert response.json()["learners_computed"] == 1
    db.expire_all()
    rows = db.scalars(select(MetricResult).where(MetricResult.revision == 2)
                      .order_by(MetricResult.academic_year)).all()
    assert [r.value for r in rows] == [0.6, 0.3]
    report = client.get("/api/v1/reports/learner/HS001", headers=auth["admin"]).json()
    assert report["metrics"][0]["latest_value"] == 0.3
    assert _compute(client, auth, definition.id).status_code == 409


def test_legacy_result_without_hash_gets_one_baseline_revision(client, db, world, auth):
    add_term(db, "HS001", cumulative_gpa=2.8)
    definition = make_definition(db, world["admin"])
    _compute(client, auth, definition.id)
    old = _results(db, definition.id)["HS001"]
    old.source_hash = None
    db.commit()
    assert _compute(client, auth, definition.id).status_code == 201
    assert _compute(client, auth, definition.id).status_code == 409
