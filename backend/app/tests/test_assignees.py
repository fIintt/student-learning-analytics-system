import pytest


URL = "/api/v1/support-cases/assignees"


def test_assignees_filter_scope_and_paginate(client, world, auth):
    response = client.get(URL + "?learner_id=HS001&size=1", headers=auth["reviewer"])
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 2 and len(response.json()["items"]) == 1
    inside = client.get(URL + "?learner_id=HS001", headers=auth["reviewer"]).json()
    assert {x["id"] for x in inside["items"]} == {world["admin"].id, world["reviewer"].id}
    assert set(inside["items"][0]) == {"id", "username", "email", "full_name", "role"}
    outside = client.get(URL + "?learner_id=HS003", headers=auth["admin"]).json()
    assert {x["id"] for x in outside["items"]} == {world["admin"].id}


def test_inactive_assignees_are_excluded(client, db, world, auth):
    world["reviewer"].is_active = False
    db.commit()
    response = client.get(URL + "?learner_id=HS001", headers=auth["admin"])
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == world["admin"].id


@pytest.mark.parametrize("query,role,code", [
    ("?learner_id=HS003", "reviewer", 403),
    ("?learner_id=HS001", "viewer", 403),
    ("?learner_id=MISSING", "admin", 404),
    ("", "admin", 400),
    ("?learner_id=HS001&size=201", "admin", 400),
])
def test_assignees_validate_request_and_permissions(client, world, auth, query, role, code):
    assert client.get(URL + query, headers=auth[role]).status_code == code


def test_assignees_require_login(client):
    assert client.get(URL + "?learner_id=HS001").status_code == 401


def test_assignment_also_rejects_outside_scope(client, world, auth, alerts):
    body = {"note": "Đã xem", "reason": "Cần hỗ trợ", "assigned_to": world["reviewer"].id}
    url = f"/api/v1/review/alerts/{alerts[2].id}/confirm"
    assert client.post(url, headers=auth["admin"], json=body).status_code == 400
    body["assigned_to"] = world["admin"].id
    created = client.post(url, headers=auth["admin"], json=body)
    assert created.status_code == 201, created.text
    case_id = created.json()["support_case"]["id"]
    assert client.patch(f"/api/v1/support-cases/{case_id}", headers=auth["admin"],
                        json={"assigned_to": world["reviewer"].id}).status_code == 400
