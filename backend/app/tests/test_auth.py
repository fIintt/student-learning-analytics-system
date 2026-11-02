from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.tests.conftest import login


def test_hash_password_roundtrip():
    hashed = hash_password("Abc@123")
    assert hashed != "Abc@123"
    assert verify_password("Abc@123", hashed)
    assert not verify_password("sai", hashed)


def test_login_success_returns_token_and_user(client, world):
    res = client.post("/api/v1/auth/login", json={"email": "Reviewer@Test.local", "password": "Test@123"})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.access_token_expire_minutes * 60
    assert body["user"] == {"id": world["reviewer"].id, "email": "reviewer@test.local",
                            "full_name": "reviewer", "role": "reviewer"}


def test_login_wrong_password_401(client, world):
    res = client.post("/api/v1/auth/login", json={"email": "admin@test.local", "password": "sai"})
    assert res.status_code == 401
    assert res.json() == {"detail": "Email hoặc mật khẩu không đúng"}


def test_login_unknown_email_401(client, world):
    res = client.post("/api/v1/auth/login", json={"email": "khongco@test.local", "password": "x"})
    assert res.status_code == 401


def test_login_inactive_user_401(client, world, db):
    world["viewer"].is_active = False
    db.commit()
    res = client.post("/api/v1/auth/login", json={"email": "viewer@test.local", "password": "Test@123"})
    assert res.status_code == 401
    assert res.json() == {"detail": "Tài khoản đã bị khoá"}


def test_login_validation_error_is_400_vietnamese(client, world):
    res = client.post("/api/v1/auth/login", json={"email": "admin@test.local"})
    assert res.status_code == 400
    assert res.json() == {"detail": "Dữ liệu không hợp lệ ở trường 'password': thiếu trường bắt buộc"}


def test_me_reviewer_sees_assigned_groups(client, world, auth):
    res = client.get("/api/v1/auth/me", headers=auth["reviewer"])
    assert res.status_code == 200
    body = res.json()
    assert body["role"] == "reviewer"
    assert body["is_active"] is True
    assert body["group_ids"] == [world["group_a"].id]


def test_me_admin_sees_all_groups(client, world, auth):
    res = client.get("/api/v1/auth/me", headers=auth["admin"])
    assert sorted(res.json()["group_ids"]) == sorted([world["group_a"].id, world["group_b"].id])


def test_me_without_token_401(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json() == {"detail": "Chưa đăng nhập"}


def test_me_with_garbage_token_401(client):
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert res.status_code == 401
    assert res.json() == {"detail": "Token không hợp lệ"}


def test_me_with_expired_token_401(client, world):
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    token = jwt.encode({"sub": str(world["admin"].id), "iat": past, "exp": past + timedelta(minutes=1)},
                       settings.secret_key, algorithm=settings.jwt_algorithm)
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert res.json() == {"detail": "Phiên đăng nhập đã hết hạn"}


def test_token_rejected_after_user_locked(client, world, db):
    headers = login(client, "viewer@test.local")
    world["viewer"].is_active = False
    db.commit()
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401


def test_unknown_route_404_vietnamese(client):
    res = client.get("/api/v1/khong-ton-tai")
    assert res.status_code == 404
    assert res.json() == {"detail": "Không tìm thấy tài nguyên"}
