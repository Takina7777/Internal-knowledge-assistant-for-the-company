"""认证模块测试：登录 / 刷新 / me / 受保护路由。"""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def _admin_credentials() -> tuple[str, str]:
    s = get_settings()
    return s.ADMIN_USERNAME, s.ADMIN_PASSWORD


def test_protected_route_requires_login():
    resp = client.get("/api/v1/documents")
    assert resp.status_code == 401
    resp = client.post("/api/v1/chat", json={"question": "测试"})
    assert resp.status_code == 401


def test_login_success_and_me():
    username, password = _admin_credentials()
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["username"] == username

    headers = {"Authorization": f"Bearer {body['access_token']}"}
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == username

    # 受保护业务路由带 token 可访问
    resp = client.get("/api/v1/documents", headers=headers)
    assert resp.status_code == 200


def test_login_wrong_password():
    username, _ = _admin_credentials()
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": "wrong-password"})
    assert resp.status_code == 401


def test_invalid_token_rejected():
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-token"})
    assert resp.status_code == 401


def test_refresh_token_rotation():
    username, password = _admin_credentials()
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    refresh = resp.json()["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]

    # 刷新令牌已轮换：旧令牌再次使用应失效
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401
