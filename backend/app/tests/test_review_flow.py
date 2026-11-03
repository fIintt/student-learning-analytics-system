import pytest

from app.main import create_app
from app.models import Alert, AlertStatus, SupportCase

ALERTS = "/api/v1/review/alerts"
CONFIRM_BODY = {"note": "Đã gọi GVCN, em vắng 2 tuần", "reason": "Ít tham gia LMS liên tục"}


# --- confirm / dismiss ------------------------------------------------------------------

def test_confirm_creates_support_case(client, db, world, auth, alerts):
    alert = alerts[0]
    res = client.post(f"{ALERTS}/{alert.id}/confirm", json={**CONFIRM_BODY, "assigned_to": world["reviewer"].id},
                      headers=auth["reviewer"])
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["alert"]["status"] == "confirmed"
    assert body["alert"]["reviewer_id"] == world["reviewer"].id
    assert body["alert"]["review_note"] == CONFIRM_BODY["note"]
    assert body["alert"]["reviewed_at"].endswith("Z")
    case = body["support_case"]
    assert body["alert"]["support_case_id"] == case["id"]
    assert case["status"] == "open"
    assert case["reason"] == CONFIRM_BODY["reason"]
    assert case["created_by"] == world["reviewer"].id      # người xác nhận
    assert case["assigned_to"] == world["reviewer"].id
    assert case["learner"]["id"] == "HS001"
    assert case["followup_count"] == 0
    assert db.query(SupportCase).count() == 1


def test_confirm_twice_409(client, db, world, auth, alerts):
    url = f"{ALERTS}/{alerts[0].id}/confirm"
    assert client.post(url, json=CONFIRM_BODY, headers=auth["reviewer"]).status_code == 201
    res = client.post(url, json=CONFIRM_BODY, headers=auth["admin"])
    assert res.status_code == 409
    assert res.json() == {"detail": "Cảnh báo đã được xử lý"}
    assert db.query(SupportCase).count() == 1


def test_confirm_after_dismiss_409(client, db, world, auth, alerts):
    url = f"{ALERTS}/{alerts[0].id}"
    assert client.post(f"{url}/dismiss", json={"note": "Nghỉ ốm có phép"}, headers=auth["reviewer"]).status_code == 200
    assert client.post(f"{url}/confirm", json=CONFIRM_BODY, headers=auth["reviewer"]).status_code == 409
    assert client.post(f"{url}/dismiss", json={"note": "lần 2"}, headers=auth["reviewer"]).status_code == 409
    assert db.query(SupportCase).count() == 0


def test_viewer_confirm_403(client, db, world, auth, alerts):
    res = client.post(f"{ALERTS}/{alerts[0].id}/confirm", json=CONFIRM_BODY, headers=auth["viewer"])
    assert res.status_code == 403
    assert client.post(f"{ALERTS}/{alerts[0].id}/dismiss", json={"note": "x"},
                       headers=auth["viewer"]).status_code == 403
    assert db.get(Alert, alerts[0].id).status == AlertStatus.PENDING_REVIEW
    assert db.query(SupportCase).count() == 0


def test_reviewer_cannot_confirm_outside_group_403(client, db, world, auth, alerts):
    res = client.post(f"{ALERTS}/{alerts[3].id}/confirm", json=CONFIRM_BODY, headers=auth["reviewer"])
    assert res.status_code == 403
    assert client.post(f"{ALERTS}/{alerts[3].id}/confirm", json=CONFIRM_BODY,
                       headers=auth["admin"]).status_code == 201


@pytest.mark.parametrize("body,message", [
    ({"reason": "x"}, "Phải nhập ghi chú khi xác nhận cảnh báo"),
    ({"note": "   ", "reason": "x"}, "Phải nhập ghi chú khi xác nhận cảnh báo"),
    ({"note": "x"}, "Phải nêu lý do cần hỗ trợ khi xác nhận cảnh báo"),
    ({}, "Phải nhập ghi chú khi xác nhận cảnh báo"),
])
def test_confirm_requires_note_and_reason_400(client, db, world, auth, alerts, body, message):
    res = client.post(f"{ALERTS}/{alerts[0].id}/confirm", json=body, headers=auth["reviewer"])
    assert res.status_code == 400
    assert res.json() == {"detail": message}
    assert db.get(Alert, alerts[0].id).status == AlertStatus.PENDING_REVIEW


def test_confirm_invalid_assignee_400(client, world, auth, alerts):
    for bad in (world["viewer"].id, 999):
        res = client.post(f"{ALERTS}/{alerts[0].id}/confirm", json={**CONFIRM_BODY, "assigned_to": bad},
                          headers=auth["reviewer"])
        assert res.status_code == 400


def test_dismiss_requires_note_and_creates_no_case(client, db, world, auth, alerts):
    url = f"{ALERTS}/{alerts[0].id}/dismiss"
    res = client.post(url, json={}, headers=auth["reviewer"])
    assert res.status_code == 400
    assert res.json() == {"detail": "Phải nhập ghi chú khi bác cảnh báo"}
    res = client.post(url, json={"note": "Nghỉ ốm có phép"}, headers=auth["reviewer"])
    assert res.status_code == 200
    assert res.json()["status"] == "dismissed"
    assert res.json()["support_case_id"] is None
    assert db.query(SupportCase).count() == 0


def test_confirm_unknown_alert_404(client, world, auth):
    assert client.post(f"{ALERTS}/999/confirm", json=CONFIRM_BODY, headers=auth["admin"]).status_code == 404


# --- không có đường nào khác tạo SupportCase ------------------------------------------------

def test_no_route_creates_support_case_except_confirm():
    app = create_app(create_tables=False)
    writes = {(m, r.path) for r in app.routes for m in getattr(r, "methods", set())
              if m in {"POST", "PUT"} and ("support" in r.path or "case" in r.path or "alert" in r.path)}
    assert writes == {("POST", "/api/v1/review/alerts/{alert_id}/confirm"),
                      ("POST", "/api/v1/review/alerts/{alert_id}/dismiss")}


def test_post_support_cases_not_allowed(client, auth, alerts):
    res = client.post("/api/v1/support-cases", json={"alert_id": alerts[0].id, "reason": "x"}, headers=auth["admin"])
    assert res.status_code == 405


def test_compute_never_creates_support_case(db, alerts):
    assert db.query(SupportCase).count() == 0
    assert all(a.status == AlertStatus.PENDING_REVIEW for a in alerts)


# --- danh sách cảnh báo theo phạm vi -------------------------------------------------------

def test_list_alerts_scoped(client, world, auth, alerts):
    assert client.get(ALERTS, headers=auth["viewer"]).status_code == 403
    assert client.get(ALERTS, headers=auth["admin"]).json()["total"] == 4

    client.post(f"{ALERTS}/{alerts[0].id}/dismiss", json={"note": "x"}, headers=auth["reviewer"])
    pending = client.get(ALERTS, params={"status": "pending_review"}, headers=auth["reviewer"]).json()
    assert pending["total"] == 1

    assert client.get(f"{ALERTS}/{alerts[0].id}", headers=auth["viewer"]).status_code == 403
    assert client.get(ALERTS, params={"learner_id": world["learners"][3].student_id},
                      headers=auth["viewer"]).status_code == 403
