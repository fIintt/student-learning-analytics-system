import pytest
from sqlalchemy import select

from app.models import MetricResult
from app.tests.test_review_flow import ALERTS, CONFIRM_BODY

CASES = "/api/v1/support-cases"
FOLLOWUPS = "/api/v1/followups"


@pytest.fixture()
def cases(client, world, auth, alerts):
    """Case của HS001 (nhóm A) và HS003 (nhóm B)."""
    out = []
    for alert in (alerts[0], alerts[2]):
        res = client.post(f"{ALERTS}/{alert.id}/confirm", json=CONFIRM_BODY, headers=auth["admin"])
        out.append(res.json()["support_case"])
    return out


# --- support cases ----------------------------------------------------------------------

def test_list_and_get_cases_scoped(client, world, auth, cases):
    assert client.get(CASES, headers=auth["admin"]).json()["total"] == 2
    assert client.get(CASES, headers=auth["viewer"]).status_code == 403
    assert client.get(f"{CASES}/{cases[1]['id']}", headers=auth["viewer"]).status_code == 403
    assert client.get(f"{CASES}/{cases[0]['id']}", headers=auth["viewer"]).status_code == 403
    assert client.get(f"{CASES}/999", headers=auth["admin"]).status_code == 404


def test_case_status_transitions(client, world, auth, cases):
    url = f"{CASES}/{cases[0]['id']}"
    res = client.patch(url, json={"status": "in_progress", "assigned_to": world["reviewer"].id},
                       headers=auth["reviewer"])
    assert res.status_code == 200
    assert (res.json()["status"], res.json()["assigned_to"]) == ("in_progress", world["reviewer"].id)

    back = client.patch(url, json={"status": "open"}, headers=auth["reviewer"])
    assert back.status_code == 409

    closed = client.patch(url, json={"status": "closed"}, headers=auth["reviewer"]).json()
    assert closed["status"] == "closed" and closed["closed_at"].endswith("Z")

    again = client.patch(url, json={"assigned_to": world["admin"].id}, headers=auth["admin"])
    assert again.status_code == 409
    assert again.json() == {"detail": "Trường hợp đã đóng"}


def test_case_open_to_closed_directly(client, auth, cases):
    res = client.patch(f"{CASES}/{cases[0]['id']}", json={"status": "closed"}, headers=auth["admin"])
    assert res.json()["status"] == "closed"


def test_case_patch_permissions(client, world, auth, cases):
    assert client.patch(f"{CASES}/{cases[0]['id']}", json={"status": "in_progress"},
                        headers=auth["viewer"]).status_code == 403
    assert client.patch(f"{CASES}/{cases[1]['id']}", json={"status": "in_progress"},
                        headers=auth["reviewer"]).status_code == 403   # ngoài nhóm
    assert client.patch(f"{CASES}/{cases[0]['id']}", json={"assigned_to": world["viewer"].id},
                        headers=auth["reviewer"]).status_code == 400
    assert client.patch(f"{CASES}/{cases[0]['id']}", json={"status": "done"},
                        headers=auth["reviewer"]).status_code == 400


# --- followups ------------------------------------------------------------------------------

def _post_result_id(db, learner_id):
    return db.scalars(select(MetricResult.id).where(MetricResult.learner_id == learner_id)).first()


def test_create_followup_with_post_metric(client, db, world, auth, cases):
    hs1 = world["learners"][0]
    result_id = _post_result_id(db, hs1.student_id)
    res = client.post(FOLLOWUPS, json={
        "case_id": cases[0]["id"], "action": "Gọi điện phụ huynh", "outcome": "Em cam kết đăng nhập mỗi ngày",
        "result_status": "improved", "post_metric_result_id": result_id,
    }, headers=auth["reviewer"])
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["action"] == "Gọi điện phụ huynh"
    assert body["result_status"] == "improved"
    assert body["performed_by"] == world["reviewer"].id
    assert body["post_metric_result"]["id"] == result_id
    assert body["post_metric_result"]["metric_code"] == "CUM_GPA"

    assert client.get(f"{CASES}/{cases[0]['id']}", headers=auth["viewer"]).status_code == 403


def test_followup_defaults_and_validation(client, db, world, auth, cases):
    ok = client.post(FOLLOWUPS, json={"case_id": cases[0]["id"], "action": "Nhắn tin"}, headers=auth["admin"])
    assert ok.json()["result_status"] == "unknown"
    assert ok.json()["post_metric_result"] is None

    no_action = client.post(FOLLOWUPS, json={"case_id": cases[0]["id"]}, headers=auth["admin"])
    assert no_action.status_code == 400
    assert no_action.json() == {"detail": "Phải mô tả hành động can thiệp"}

    other_learner = _post_result_id(db, world["learners"][1].student_id)
    wrong = client.post(FOLLOWUPS, json={"case_id": cases[0]["id"], "action": "x",
                                         "post_metric_result_id": other_learner}, headers=auth["admin"])
    assert wrong.status_code == 400

    bad_status = client.post(FOLLOWUPS, json={"case_id": cases[0]["id"], "action": "x", "result_status": "great"},
                             headers=auth["admin"])
    assert bad_status.status_code == 400
    assert client.post(FOLLOWUPS, json={"case_id": 999, "action": "x"}, headers=auth["admin"]).status_code == 404


def test_followup_permissions_and_closed_case(client, world, auth, cases):
    body = {"case_id": cases[0]["id"], "action": "x"}
    assert client.post(FOLLOWUPS, json=body, headers=auth["viewer"]).status_code == 403
    assert client.post(FOLLOWUPS, json={**body, "case_id": cases[1]["id"]},
                       headers=auth["reviewer"]).status_code == 403
    client.patch(f"{CASES}/{cases[0]['id']}", json={"status": "closed"}, headers=auth["admin"])
    res = client.post(FOLLOWUPS, json=body, headers=auth["admin"])
    assert res.status_code == 409


def test_list_followups_scoped(client, world, auth, cases):
    for case in cases:
        client.post(FOLLOWUPS, json={"case_id": case["id"], "action": "x"}, headers=auth["admin"])
    assert client.get(FOLLOWUPS, headers=auth["admin"]).json()["total"] == 2
    assert client.get(FOLLOWUPS, headers=auth["viewer"]).status_code == 403
    assert client.get(FOLLOWUPS, params={"case_id": cases[1]["id"]}, headers=auth["viewer"]).status_code == 403
    assert client.get(FOLLOWUPS, params={"case_id": cases[0]["id"]}, headers=auth["viewer"]).status_code == 403
