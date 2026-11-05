from sqlalchemy import select

from app.models import AuditLog

DEFS = "/api/v1/metric-definitions"
CONFIRM = {"note": "Đã kiểm tra", "reason": "Cần hỗ trợ"}


def _logs(db, action=None):
    db.expire_all()
    stmt = select(AuditLog).order_by(AuditLog.id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    return db.scalars(stmt).all()


def _pending_definition(client, auth, code="LOGIN"):
    d = client.post(DEFS, json={
        "code": code, "name": code, "purpose": "Hỗ trợ sinh viên", "formula_type": "cumulative_gpa",
        "formula_params": {}, "threshold": {"operator": "<", "value": 2.0},
    }, headers=auth["reviewer"]).json()
    client.post(f"{DEFS}/{d['id']}/submit", headers=auth["reviewer"])
    return d


def test_metric_approve_and_reject_are_audited(client, db, world, auth):
    v1 = _pending_definition(client, auth)
    client.post(f"{DEFS}/{v1['id']}/approve", json={"note": "Đồng ý"}, headers=auth["admin"])
    [approve] = _logs(db, "metric.approve")
    assert (approve.user_id, approve.entity_type, approve.entity_id) == (world["admin"].id, "metric_definition",
                                                                         v1["id"])
    assert approve.detail == {"code": "LOGIN", "version": 1, "note": "Đồng ý", "retired_ids": []}

    v2 = client.post(f"{DEFS}/{v1['id']}/new-version", headers=auth["reviewer"]).json()
    client.post(f"{DEFS}/{v2['id']}/submit", headers=auth["reviewer"])
    client.post(f"{DEFS}/{v2['id']}/approve", headers=auth["admin"])
    assert _logs(db, "metric.approve")[1].detail == {"code": "LOGIN", "version": 2, "note": None,
                                                     "retired_ids": [v1["id"]]}

    other = _pending_definition(client, auth, code="OTHER")
    client.post(f"{DEFS}/{other['id']}/reject", json={"note": "Ngưỡng chưa hợp lý"}, headers=auth["admin"])
    [reject] = _logs(db, "metric.reject")
    assert reject.entity_id == other["id"]
    assert reject.detail == {"code": "OTHER", "version": 1, "note": "Ngưỡng chưa hợp lý"}


def test_failed_approve_not_audited(client, db, world, auth):
    d = _pending_definition(client, auth)
    client.post(f"{DEFS}/{d['id']}/approve", headers=auth["reviewer"])          # 403
    client.post(f"{DEFS}/{d['id']}/reject", json={}, headers=auth["admin"])      # 400
    client.post(f"{DEFS}/{d['id']}/approve", headers=auth["admin"])              # OK
    client.post(f"{DEFS}/{d['id']}/approve", headers=auth["admin"])              # 409
    assert len(_logs(db, "metric.approve")) == 1
    assert _logs(db, "metric.reject") == []


def test_confirm_audits_alert_and_case(client, db, world, auth, alerts):
    body = client.post(f"/api/v1/review/alerts/{alerts[0].id}/confirm",
                       json={**CONFIRM, "assigned_to": world["reviewer"].id}, headers=auth["reviewer"]).json()
    case_id = body["support_case"]["id"]

    [confirm] = _logs(db, "alert.confirm")
    assert (confirm.user_id, confirm.entity_type, confirm.entity_id) == (world["reviewer"].id, "alert", alerts[0].id)
    assert confirm.detail == {"note": "Đã kiểm tra", "reason": "Cần hỗ trợ", "support_case_id": case_id}

    [case] = _logs(db, "case.create")
    assert (case.user_id, case.entity_type, case.entity_id) == (world["reviewer"].id, "support_case", case_id)
    assert case.detail == {"alert_id": alerts[0].id, "learner_id": world["learners"][0].student_id,
                           "assigned_to": world["reviewer"].id}

    # xác nhận lần 2 (409) không ghi thêm
    client.post(f"/api/v1/review/alerts/{alerts[0].id}/confirm", json=CONFIRM, headers=auth["admin"])
    assert len(_logs(db, "alert.confirm")) == 1 and len(_logs(db, "case.create")) == 1


def test_dismiss_is_audited(client, db, world, auth, alerts):
    client.post(f"/api/v1/review/alerts/{alerts[1].id}/dismiss", json={"note": "Nghỉ ốm"}, headers=auth["reviewer"])
    [log] = _logs(db, "alert.dismiss")
    assert (log.user_id, log.entity_id, log.detail) == (world["reviewer"].id, alerts[1].id, {"note": "Nghỉ ốm"})
    # viewer bị chặn (403) → không có nhật ký
    client.post(f"/api/v1/review/alerts/{alerts[0].id}/dismiss", json={"note": "x"}, headers=auth["viewer"])
    assert len(_logs(db, "alert.dismiss")) == 1
