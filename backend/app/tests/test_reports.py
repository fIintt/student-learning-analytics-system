import pytest

from app.models import Program, Student
from app.tests.conftest import add_term, make_definition

REPORTS = "/api/v1/reports"
CONFIRM = {"note": "Đã kiểm tra", "reason": "Cần hỗ trợ"}


@pytest.fixture()
def scenario(client, db, world, auth):
    """Hai chỉ số: CUM (GPA tích luỹ < 2.0) và FAILED (tỷ lệ tín chỉ rớt kỳ gần nhất > 0.25).

    Học kỳ 2024-2025 HK2: HS001 GPA 1.5 và rớt 6/21 (cảnh báo cả hai); HS002 GPA 3.0; HS003 GPA 1.8
    (cảnh báo CUM); HS004 GPA 2.5. Sau đó HS001 có học kỳ mới 2025-2026 HK1 với GPA 2.2 (hết cảnh báo CUM).
    """
    add_term(db, "HS001", "2024-2025", 2, registered=21, failed=6, cumulative_gpa=1.5)
    add_term(db, "HS002", "2024-2025", 2, cumulative_gpa=3.0)
    add_term(db, "HS003", "2024-2025", 2, cumulative_gpa=1.8)
    add_term(db, "HS004", "2024-2025", 2, cumulative_gpa=2.5)

    cum = make_definition(db, world["admin"], code="CUM")
    failed = make_definition(db, world["admin"], code="FAILED", formula_type="failed_credit_ratio",
                             formula_params={"terms": 1}, threshold={"operator": ">", "value": 0.25})
    for definition in (cum, failed):
        assert client.post("/api/v1/metrics/compute", json={"metric_definition_id": definition.id},
                           headers=auth["admin"]).status_code == 201
    add_term(db, "HS001", "2025-2026", 1, cumulative_gpa=2.2)
    assert client.post("/api/v1/metrics/compute", json={"metric_definition_id": cum.id},
                       headers=auth["admin"]).json()["learners_computed"] == 1

    alerts = client.get("/api/v1/review/alerts?size=200", headers=auth["admin"]).json()["items"]
    by = {(a["learner"]["id"], a["metric_result"]["metric_code"]): a["id"] for a in alerts}
    assert set(by) == {("HS001", "CUM"), ("HS001", "FAILED"), ("HS003", "CUM")}
    # HS001/FAILED được xác nhận → có case; HS003/CUM bị bác
    case = client.post(f"/api/v1/review/alerts/{by[('HS001', 'FAILED')]}/confirm", json=CONFIRM,
                       headers=auth["admin"]).json()["support_case"]
    client.post("/api/v1/followups", json={"case_id": case["id"], "action": "Tư vấn học lại",
                                           "result_status": "improved"}, headers=auth["admin"])
    client.post(f"/api/v1/review/alerts/{by[('HS003', 'CUM')]}/dismiss", json={"note": "Đã có kế hoạch học lại"},
                headers=auth["admin"])
    return {"case": case}


# --- báo cáo người học -----------------------------------------------------------------

def test_learner_report(client, world, auth, scenario):
    res = client.get(f"{REPORTS}/learner/HS001", headers=auth["viewer"])
    assert res.status_code == 200
    body = res.json()
    assert body["learner"] == {
        "id": "HS001", "full_name": "Học sinh 1",
        "program": {"id": "P1", "name": "Chương trình 1", "name_en": "Program 1", "program_type": "Standard"},
        "cohort": 2022, "academic_status": "studying",
        "groups": [{"id": world["group_a"].id, "name": "P1-2022"}],
    }

    metrics = {m["metric_code"]: m for m in body["metrics"]}
    cum = metrics["CUM"]
    assert (cum["latest_value"], cum["flagged"], cum["academic_year"], cum["semester"]) == (2.2, False, "2025-2026", 1)
    assert [(h["value"], h["academic_year"], h["semester"]) for h in cum["history"]] == [
        (2.2, "2025-2026", 1), (1.5, "2024-2025", 2)]
    assert (metrics["FAILED"]["latest_value"], metrics["FAILED"]["flagged"]) == (0.2857, True)

    assert body["alerts"] == {"pending_review": 1, "confirmed": 1, "dismissed": 0}
    assert body["support_cases"] == [{
        "id": scenario["case"]["id"], "status": "open", "reason": "Cần hỗ trợ",
        "created_at": scenario["case"]["created_at"], "followup_count": 1, "latest_result_status": "improved",
    }]


def test_learner_report_without_data(client, db, world, auth):
    res = client.get(f"{REPORTS}/learner/HS001", headers=auth["reviewer"]).json()
    assert res["metrics"] == [] and res["support_cases"] == []
    assert res["alerts"] == {"pending_review": 0, "confirmed": 0, "dismissed": 0}


def test_learner_report_permissions(client, world, auth):
    res = client.get(f"{REPORTS}/learner/HS004", headers=auth["viewer"])
    assert res.status_code == 403
    assert res.json() == {"detail": "Bạn không có quyền xem người học này"}
    assert client.get(f"{REPORTS}/learner/HS004", headers=auth["reviewer"]).status_code == 403
    assert client.get(f"{REPORTS}/learner/HS004", headers=auth["admin"]).status_code == 200
    assert client.get(f"{REPORTS}/learner/KHONG-CO", headers=auth["admin"]).status_code == 404
    assert client.get(f"{REPORTS}/learner/HS004").status_code == 401


# --- báo cáo nhóm --------------------------------------------------------------------------

def test_group_report(client, world, auth, scenario):
    res = client.get(f"{REPORTS}/group/{world['group_a'].id}", headers=auth["viewer"])
    assert res.status_code == 200
    body = res.json()
    assert body["scope"] == {"type": "group", "id": world["group_a"].id, "name": "P1-2022"}
    assert body["learner_count"] == 2

    metrics = {m["metric_code"]: m for m in body["metrics"]}
    # CUM: HS001 mới nhất 2.2 (học kỳ mới), HS002 3.0 → không ai bị cảnh báo
    assert metrics["CUM"] == {"metric_code": "CUM", "metric_version": 1, "learners_with_result": 2,
                              "avg_value": 2.6, "min_value": 2.2, "max_value": 3.0,
                              "flagged_count": 0, "flagged_ratio": 0.0}
    assert (metrics["FAILED"]["avg_value"], metrics["FAILED"]["flagged_count"],
            metrics["FAILED"]["flagged_ratio"]) == (0.14, 1, 0.5)

    assert body["alerts"] == {"pending_review": 1, "confirmed": 1, "dismissed": 0}
    assert body["support_cases"] == {"open": 1, "in_progress": 0, "closed": 0}
    assert body["followups"] == {"unknown": 0, "improved": 1, "no_change": 0, "worsened": 0}
    assert body["learners_needing_support"] == [{
        "id": "HS001", "full_name": "Học sinh 1", "flagged_metrics": ["FAILED"], "open_case": True,
    }]


def test_group_report_other_group_only_counts_its_learners(client, world, auth, scenario):
    body = client.get(f"{REPORTS}/group/{world['group_b'].id}", headers=auth["admin"]).json()
    assert body["learner_count"] == 2
    assert body["alerts"] == {"pending_review": 0, "confirmed": 0, "dismissed": 1}
    assert [l["id"] for l in body["learners_needing_support"]] == ["HS003"]


def test_group_report_permissions(client, world, auth):
    res = client.get(f"{REPORTS}/group/{world['group_b'].id}", headers=auth["viewer"])
    assert res.status_code == 403
    assert res.json() == {"detail": "Bạn không có quyền xem nhóm này"}
    assert client.get(f"{REPORTS}/group/{world['group_b'].id}", headers=auth["reviewer"]).status_code == 403
    assert client.get(f"{REPORTS}/group/999", headers=auth["admin"]).status_code == 404


# --- báo cáo chương trình ------------------------------------------------------------------

def test_program_report_scoped_to_viewer_groups(client, world, auth, scenario):
    url = f"{REPORTS}/program/P1"
    admin = client.get(url, headers=auth["admin"]).json()
    assert admin["scope"] == {"type": "program", "id": "P1", "name": "Chương trình 1"}
    assert admin["learner_count"] == 4
    assert admin["alerts"] == {"pending_review": 1, "confirmed": 1, "dismissed": 1}

    viewer = client.get(url, headers=auth["viewer"]).json()
    assert viewer["learner_count"] == 2          # chỉ sinh viên thuộc nhóm A
    assert viewer["alerts"] == {"pending_review": 1, "confirmed": 1, "dismissed": 0}
    assert {l["id"] for l in viewer["learners_needing_support"]} == {"HS001"}


def test_program_report_permissions(client, db, world, auth):
    db.add(Program(program_id="P2", program_name_vi="Chương trình 2", program_name_en="Program 2",
                   major_code="7340201", program_type="EP", first_cohort_year=2020, last_cohort_year=2026))
    db.flush()
    db.add(Student(student_id="HS100", name="Học sinh 100", program_id="P2", cohort=2022,
                   academic_status="studying"))  # không thuộc nhóm nào của viewer
    db.commit()
    res = client.get(f"{REPORTS}/program/P2", headers=auth["viewer"])
    assert res.status_code == 403
    assert res.json() == {"detail": "Bạn không có quyền xem chương trình này"}
    assert client.get(f"{REPORTS}/program/P2", headers=auth["admin"]).json()["learner_count"] == 1
    assert client.get(f"{REPORTS}/program/KHONG-CO", headers=auth["admin"]).status_code == 404
