import pytest

from app.models import MetricDefinition

BASE = "/api/v1/metric-definitions"

FAILED_RATIO = {
    "code": "FAILED_RATIO",
    "name": "Tỷ lệ tín chỉ rớt học kỳ gần nhất",
    "purpose": "Nhận diện sinh viên rớt nhiều tín chỉ để tư vấn kế hoạch học tập",
    "formula_type": "failed_credit_ratio",
    "formula_params": {"terms": 1},
    "threshold": {"operator": ">", "value": 0.4},
}


def _create(client, headers, **overrides):
    res = client.post(BASE, json={**FAILED_RATIO, **overrides}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def _approved(client, auth, **overrides):
    d = _create(client, auth["reviewer"], **overrides)
    assert client.post(f"{BASE}/{d['id']}/submit", headers=auth["reviewer"]).status_code == 200
    res = client.post(f"{BASE}/{d['id']}/approve", headers=auth["admin"])
    assert res.status_code == 200, res.text
    return res.json()


# --- tạo và kiểm tra tham số ---------------------------------------------------------

def test_create_draft(client, world, auth):
    d = _create(client, auth["reviewer"])
    assert d["status"] == "draft"
    assert d["version"] == 1
    assert d["created_by"] == world["reviewer"].id
    assert d["approved_by"] is None and d["approved_at"] is None
    assert d["threshold"] == {"operator": ">", "value": 0.4}


def test_create_allows_empty_purpose_in_draft(client, world, auth):
    assert _create(client, auth["reviewer"], purpose="")["purpose"] == ""


def test_create_duplicate_code_409(client, world, auth):
    _create(client, auth["reviewer"])
    res = client.post(BASE, json=FAILED_RATIO, headers=auth["admin"])
    assert res.status_code == 409
    assert res.json() == {"detail": "Mã công thức đã tồn tại"}


@pytest.mark.parametrize("formula_type,params", [
    ("failed_credit_ratio", {"terms": 0}),             # terms phải > 0
    ("failed_credit_ratio", {"terms": "abc"}),         # không phải số nguyên
    ("failed_credit_ratio", {"terms": 1, "x": 1}),     # tham số lạ
    ("cumulative_gpa", {"terms": 1}),                  # cumulative_gpa không có tham số
])
def test_create_invalid_params_400(client, world, auth, formula_type, params):
    res = client.post(BASE, json={**FAILED_RATIO, "formula_type": formula_type, "formula_params": params},
                      headers=auth["reviewer"])
    assert res.status_code == 400
    assert res.json()["detail"].startswith(f"Tham số công thức không hợp lệ cho loại {formula_type}")


@pytest.mark.parametrize("formula_type,params", [
    ("failed_credit_ratio", {"terms": 2}),
    ("failed_credit_ratio", {}),
    ("cumulative_gpa", {}),
])
def test_create_valid_params(client, world, auth, formula_type, params):
    d = _create(client, auth["reviewer"], formula_type=formula_type, formula_params=params)
    assert d["formula_type"] == formula_type


def test_create_invalid_threshold_or_type_400(client, world, auth):
    bad_op = client.post(BASE, json={**FAILED_RATIO, "threshold": {"operator": "!=", "value": 1}},
                         headers=auth["reviewer"])
    assert bad_op.status_code == 400
    bad_type = client.post(BASE, json={**FAILED_RATIO, "formula_type": "magic"}, headers=auth["reviewer"])
    assert bad_type.status_code == 400


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_create_non_finite_threshold_400(client, world, auth, value):
    res = client.post(BASE, json={**FAILED_RATIO, "threshold": {"operator": ">", "value": value}},
                      headers=auth["reviewer"])
    assert res.status_code == 400


def test_viewer_cannot_create_but_can_read(client, world, auth):
    d = _create(client, auth["reviewer"])
    assert client.post(BASE, json={**FAILED_RATIO, "code": "X"}, headers=auth["viewer"]).status_code == 403
    assert client.get(f"{BASE}/{d['id']}", headers=auth["viewer"]).status_code == 200
    assert client.get(BASE, headers=auth["viewer"]).json()["total"] == 1


# --- vòng đời -------------------------------------------------------------------------

def test_full_lifecycle_draft_pending_approved(client, world, auth):
    d = _create(client, auth["reviewer"])
    pending = client.post(f"{BASE}/{d['id']}/submit", headers=auth["reviewer"]).json()
    assert pending["status"] == "pending"
    approved = client.post(f"{BASE}/{d['id']}/approve", json={"note": "OK"}, headers=auth["admin"]).json()
    assert approved["status"] == "approved"
    assert approved["approved_by"] == world["admin"].id
    assert approved["approved_at"].endswith("Z")


def test_submit_requires_purpose_400(client, world, auth):
    d = _create(client, auth["reviewer"], purpose="   ")
    res = client.post(f"{BASE}/{d['id']}/submit", headers=auth["reviewer"])
    assert res.status_code == 400
    assert res.json() == {"detail": "Phải nêu mục đích sử dụng trước khi gửi duyệt"}
    # bổ sung mục đích rồi gửi lại được
    client.patch(f"{BASE}/{d['id']}", json={"purpose": "Hỗ trợ học sinh"}, headers=auth["reviewer"])
    assert client.post(f"{BASE}/{d['id']}/submit", headers=auth["reviewer"]).json()["status"] == "pending"


def test_submit_twice_409(client, world, auth):
    d = _create(client, auth["reviewer"])
    client.post(f"{BASE}/{d['id']}/submit", headers=auth["reviewer"])
    assert client.post(f"{BASE}/{d['id']}/submit", headers=auth["reviewer"]).status_code == 409


def test_only_admin_can_approve_or_reject(client, world, auth):
    d = _create(client, auth["reviewer"])
    client.post(f"{BASE}/{d['id']}/submit", headers=auth["reviewer"])
    for role in ("reviewer", "viewer"):
        assert client.post(f"{BASE}/{d['id']}/approve", headers=auth[role]).status_code == 403
        assert client.post(f"{BASE}/{d['id']}/reject", json={"note": "x"}, headers=auth[role]).status_code == 403


def test_approve_draft_409(client, world, auth):
    d = _create(client, auth["reviewer"])
    res = client.post(f"{BASE}/{d['id']}/approve", headers=auth["admin"])
    assert res.status_code == 409
    assert res.json() == {"detail": "Chỉ phê duyệt được công thức đang chờ duyệt"}


def test_reject_requires_note_and_allows_edit_back_to_draft(client, world, auth):
    d = _create(client, auth["reviewer"])
    client.post(f"{BASE}/{d['id']}/submit", headers=auth["reviewer"])
    assert client.post(f"{BASE}/{d['id']}/reject", json={"note": "  "}, headers=auth["admin"]).status_code == 400
    assert client.post(f"{BASE}/{d['id']}/reject", json={}, headers=auth["admin"]).status_code == 400
    rejected = client.post(f"{BASE}/{d['id']}/reject", json={"note": "Ngưỡng quá thấp"}, headers=auth["admin"])
    assert rejected.json()["status"] == "rejected"
    assert client.post(f"{BASE}/{d['id']}/approve", headers=auth["admin"]).status_code == 409

    edited = client.patch(f"{BASE}/{d['id']}", json={"threshold": {"operator": "<", "value": 3}},
                          headers=auth["reviewer"]).json()
    assert edited["status"] == "draft"
    assert edited["threshold"]["value"] == 3


def test_cannot_patch_pending_or_approved_409(client, world, auth):
    d = _approved(client, auth)
    res = client.patch(f"{BASE}/{d['id']}", json={"name": "Đổi tên"}, headers=auth["reviewer"])
    assert res.status_code == 409
    assert res.json() == {"detail": "Chỉ sửa được công thức ở trạng thái nháp hoặc bị từ chối"}


def test_patch_invalid_params_400(client, world, auth):
    d = _create(client, auth["reviewer"])
    res = client.patch(f"{BASE}/{d['id']}", json={"formula_params": {"terms": 0}},
                       headers=auth["reviewer"])
    assert res.status_code == 400


# --- phiên bản mới ------------------------------------------------------------------------

def test_new_version_keeps_old_and_retires_on_approve(client, db, world, auth):
    v1 = _approved(client, auth)
    res = client.post(f"{BASE}/{v1['id']}/new-version", json={"threshold": {"operator": "<", "value": 5}},
                      headers=auth["reviewer"])
    assert res.status_code == 201
    v2 = res.json()
    assert (v2["code"], v2["version"], v2["status"]) == ("FAILED_RATIO", 2, "draft")
    assert v2["threshold"]["value"] == 5
    assert v2["formula_params"] == v1["formula_params"]

    # bản cũ không bị ghi đè và vẫn đang được dùng
    old = client.get(f"{BASE}/{v1['id']}", headers=auth["viewer"]).json()
    assert old["status"] == "approved" and old["threshold"]["value"] == 0.4

    client.post(f"{BASE}/{v2['id']}/submit", headers=auth["reviewer"])
    client.post(f"{BASE}/{v2['id']}/approve", headers=auth["admin"])
    assert client.get(f"{BASE}/{v1['id']}", headers=auth["admin"]).json()["status"] == "retired"
    assert client.get(f"{BASE}/{v2['id']}", headers=auth["admin"]).json()["status"] == "approved"
    assert db.query(MetricDefinition).count() == 2


def test_new_version_only_from_approved_409(client, world, auth):
    d = _create(client, auth["reviewer"])
    res = client.post(f"{BASE}/{d['id']}/new-version", headers=auth["reviewer"])
    assert res.status_code == 409
    assert res.json() == {"detail": "Chỉ tạo phiên bản mới từ công thức đã được phê duyệt"}


def test_new_version_blocked_while_another_in_progress_409(client, world, auth):
    v1 = _approved(client, auth)
    assert client.post(f"{BASE}/{v1['id']}/new-version", headers=auth["reviewer"]).status_code == 201
    res = client.post(f"{BASE}/{v1['id']}/new-version", headers=auth["reviewer"])
    assert res.status_code == 409
    assert res.json() == {"detail": "Công thức này đã có phiên bản mới đang soạn hoặc chờ duyệt"}


def test_list_filters(client, world, auth):
    _approved(client, auth)
    _create(client, auth["reviewer"], code="AVG", formula_type="cumulative_gpa", formula_params={})
    assert client.get(BASE, params={"status": "approved"}, headers=auth["admin"]).json()["total"] == 1
    assert client.get(BASE, params={"code": "AVG"}, headers=auth["admin"]).json()["items"][0]["status"] == "draft"
    assert client.get(f"{BASE}/999", headers=auth["admin"]).status_code == 404
