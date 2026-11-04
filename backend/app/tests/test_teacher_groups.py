import pytest

BASE = "/api/v1/admin/teacher-accounts"


def test_teacher_discovery(client, world, auth):
    response = client.get(BASE + "?size=1", headers=auth["admin"])
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    teacher = body["items"][0]
    assert teacher["id"] == world["reviewer"].id
    assert teacher["username"] == "reviewer@test.local"
    assert teacher["group_ids"] == [world["group_a"].id]
    assert "hashed_password" not in teacher


def test_replace_groups_updates_scope_on_existing_token(client, world, auth, alerts):
    url = f"{BASE}/{world['reviewer'].id}/groups"
    a, b = world["group_a"].id, world["group_b"].id
    headers = auth["reviewer"]
    assert client.put(url, json={"group_ids": [b,b]}, headers=auth["admin"]).json()["group_ids"] == [b]
    assert client.get("/api/v1/auth/me", headers=headers).json()["group_ids"] == [b]
    assert client.get("/api/v1/learners", headers=headers).json()["total"] == 2
    assert client.get("/api/v1/reports/learner/HS001", headers=headers).status_code == 403
    assert client.get("/api/v1/reports/learner/HS003", headers=headers).status_code == 200
    assignees = client.get("/api/v1/support-cases/assignees?learner_id=HS001", headers=auth["admin"]).json()["items"]
    assert world["reviewer"].id not in {u["id"] for u in assignees}
    response = client.put(url, json={"group_ids": [a,b]}, headers=auth["admin"])
    assert response.json()["group_ids"] == sorted([a,b])
    assert client.get("/api/v1/learners", headers=headers).json()["total"] == 4
    assert client.put(url, json={"group_ids": []}, headers=auth["admin"]).json()["group_ids"] == []
    assert client.get("/api/v1/learners", headers=headers).json()["total"] == 0
    assert client.get("/api/v1/review/alerts", headers=headers).json()["total"] == 0
    assert client.get("/api/v1/reports/learner/HS003", headers=headers).status_code == 403
    # Student's own access does not depend on teacher assignments.
    assert client.get("/api/v1/reports/learner/HS001", headers=auth["viewer"]).status_code == 200


def test_invalid_groups_do_not_change_permissions(client, world, auth):
    url = f"{BASE}/{world['reviewer'].id}/groups"
    assert client.put(url, json={"group_ids": [world["group_b"].id,999999]}, headers=auth["admin"]).status_code == 400
    assert client.get("/api/v1/auth/me", headers=auth["reviewer"]).json()["group_ids"] == [world["group_a"].id]
    for body in ({}, {"group_ids":None}, {"group_ids":[0]}, {"group_ids":[True]}, {"group_ids":["1"]}):
        assert client.put(url, json=body, headers=auth["admin"]).status_code == 400


@pytest.mark.parametrize("role", ["viewer", "reviewer"])
def test_only_admin_assigns_groups(client, world, auth, role):
    assert client.get(BASE, headers=auth[role]).status_code == 403
    assert client.put(f"{BASE}/{world['reviewer'].id}/groups", json={"group_ids":[]}, headers=auth[role]).status_code == 403


def test_missing_and_wrong_role(client, world, auth):
    for role in ("admin", "viewer"):
        assert client.put(f"{BASE}/{world[role].id}/groups", json={"group_ids":[]}, headers=auth["admin"]).status_code == 400
    assert client.put(f"{BASE}/999999/groups", json={"group_ids":[]}, headers=auth["admin"]).status_code == 404
    assert client.get(BASE).status_code == 401
    assert client.put(f"{BASE}/{world['reviewer'].id}/groups", json={"group_ids":[]}).status_code == 401
