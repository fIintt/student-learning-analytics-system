from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.core.permissions import (
    accessible_group_ids,
    can_access_learner,
    ensure_group_access,
    require_roles,
    scope_by_learner,
)
from app.models import Role, Student, User


def _learner_ids_visible_to(db, user):
    stmt = scope_by_learner(select(Student.student_id), Student.student_id, user)
    return set(db.scalars(stmt).all())


def test_viewer_only_sees_learners_in_own_group(db, world):
    in_group = {l.student_id for l in world["learners"][:2]}
    assert _learner_ids_visible_to(db, world["viewer"]) == in_group
    outside = world["learners"][3]
    assert can_access_learner(db, world["viewer"], outside.student_id) is False
    assert can_access_learner(db, world["viewer"], world["learners"][0].student_id) is True


def test_viewer_cannot_view_learner_outside_group_via_api(client, world, auth, alerts):
    """Kiểm tra qua API: mọi endpoint có dữ liệu người học đều chặn hoặc lọc người ngoài nhóm."""
    inside, outside = world["learners"][0], world["learners"][3]
    headers = auth["viewer"]

    assert client.get(f"/api/v1/reports/learner/{outside.student_id}", headers=headers).status_code == 403
    assert client.get(f"/api/v1/reports/learner/{inside.student_id}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/review/alerts/{alerts[3].id}", headers=headers).status_code == 403
    for url in ("/api/v1/metrics/results", "/api/v1/review/alerts", "/api/v1/support-cases"):
        assert client.get(url, params={"learner_id": outside.student_id}, headers=headers).status_code == 403

    listed = client.get("/api/v1/review/alerts", headers=headers).json()["items"]
    assert outside.student_id not in {a["learner"]["id"] for a in listed}
    results = client.get("/api/v1/metrics/results", headers=headers).json()["items"]
    assert outside.student_id not in {r["learner_id"] for r in results}


def test_reviewer_sees_assigned_groups_only(db, world):
    assert accessible_group_ids(db, world["reviewer"]) == [world["group_a"].id]
    assert _learner_ids_visible_to(db, world["reviewer"]) == {l.student_id for l in world["learners"][:2]}


def test_reviewer_with_two_groups_sees_both(db, world):
    world["reviewer"].groups.append(world["group_b"])
    db.commit()
    assert _learner_ids_visible_to(db, world["reviewer"]) == {l.student_id for l in world["learners"]}


def test_admin_sees_everything(db, world):
    assert _learner_ids_visible_to(db, world["admin"]) == {l.student_id for l in world["learners"]}
    assert can_access_learner(db, world["admin"], world["learners"][3].student_id)


def test_user_without_groups_sees_nothing(db, world):
    lonely = User(email="x@test.local", full_name="x", hashed_password="-", role=Role.VIEWER, is_active=True)
    db.add(lonely)
    db.commit()
    assert _learner_ids_visible_to(db, lonely) == set()


def test_ensure_group_access_outside_group_403(db, world):
    import pytest
    from fastapi import HTTPException

    ensure_group_access(db, world["viewer"], world["group_a"].id)
    with pytest.raises(HTTPException) as exc:
        ensure_group_access(db, world["viewer"], world["group_b"].id)
    assert exc.value.status_code == 403
    ensure_group_access(db, world["admin"], world["group_b"].id)


def test_require_roles_dependency(app, client, auth):
    router = APIRouter()

    @router.get("/_test/admin-only")
    def _admin_only(user: User = Depends(require_roles(Role.ADMIN))):
        return {"ok": user.id}

    @router.get("/_test/staff")
    def _staff(user: User = Depends(require_roles(Role.ADMIN, Role.REVIEWER))):
        return {"ok": user.id}

    app.include_router(router)

    assert client.get("/_test/admin-only", headers=auth["admin"]).status_code == 200
    res = client.get("/_test/admin-only", headers=auth["reviewer"])
    assert res.status_code == 403
    assert res.json() == {"detail": "Bạn không có quyền thực hiện thao tác này"}
    assert client.get("/_test/staff", headers=auth["reviewer"]).status_code == 200
    assert client.get("/_test/staff", headers=auth["viewer"]).status_code == 403
    assert client.get("/_test/staff").status_code == 401
