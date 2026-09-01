"""健康检查路由测试（不依赖外部服务）。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["vector_store"] in {"chroma", "qdrant"}
