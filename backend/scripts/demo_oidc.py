"""SSO/OIDC 无真实环境演示：本地起一个"假 IdP"（JWKS 端点）+ 自签 ID Token，
验证 OidcAuthProvider 校验与受保护接口全链路（无需公司 IdP）。

用法（在 backend 目录下）：
    .venv\\Scripts\\python scripts\\demo_oidc.py
预期：
    [1] provider 校验 -> 返回映射后的用户信息（含部门/密级）
    [2] GET /api/v1/auth/me 携带 ID Token -> 200（真实路由 + 真实鉴权依赖）
    [3] 错误 audience 的 Token -> 401
"""

import base64
import http.server
import json
import os
import sys
import threading
import time
from pathlib import Path

# 保证从任意目录运行时都能 import app 包（必须在 import app.* 之前设置环境变量）
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

from cryptography.hazmat.primitives.asymmetric import rsa

KID = "demo-kid"
CLIENT_ID = "ek-web"

# ---- 1. 生成本地 IdP 的 RSA 密钥与 JWKS ----
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
nums = private_key.public_key().public_numbers()


def _b64u(i: int) -> str:
    length = (i.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(i.to_bytes(length, "big")).rstrip(b"=").decode()


JWKS = {"keys": [{"kty": "RSA", "kid": KID, "use": "sig", "alg": "RS256",
                  "n": _b64u(nums.n), "e": _b64u(nums.e)}]}

ISSUER = ""  # 占位，起服务后赋值


class IdPHandler(http.server.BaseHTTPRequestHandler):
    """假 IdP：提供 openid-configuration 与 jwks 端点。"""

    def do_GET(self):  # noqa: N802
        if self.path == "/.well-known/openid-configuration":
            body = json.dumps({"issuer": ISSUER, "jwks_uri": f"{ISSUER}/jwks"}).encode()
        elif self.path == "/jwks":
            body = json.dumps(JWKS).encode()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # noqa: D102
        pass


_server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), IdPHandler)
ISSUER = f"http://127.0.0.1:{_server.server_address[1]}"
threading.Thread(target=_server.serve_forever, daemon=True).start()

# ---- 2. 设置环境变量（必须在 import app.* 之前）----
os.environ["AUTH_PROVIDER"] = "oidc"
os.environ["OIDC_ISSUER"] = ISSUER
os.environ["OIDC_CLIENT_ID"] = CLIENT_ID
os.environ["OIDC_JWKS_URI"] = f"{ISSUER}/jwks"

import jwt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.api.deps import OidcAuthProvider  # noqa: E402
from app.main import app  # noqa: E402


def _mint(**overrides) -> str:
    claims = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "sub": "u-1001",
        "preferred_username": "zhangsan",
        "name": "张三",
        "role": "user",
        "department": "hr",
        "clearance": 3,
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
        **overrides,
    }
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": KID})


def main() -> None:
    print("== 本地假 IdP 已启动:", ISSUER)

    print("\n== [1] OidcAuthProvider 校验（含 JWKS 拉取）==")
    provider = OidcAuthProvider()
    token = _mint()
    user = provider.authenticate(token)
    assert user, "合法 ID Token 校验失败"
    print("   OK 用户:", {k: user[k] for k in ("id", "username", "role", "department", "clearance")})

    print("\n== [2] 真实受保护接口（/api/v1/auth/me，走 AUTH_PROVIDER=oidc 依赖）==")
    client = TestClient(app)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    print(f"   状态 {resp.status_code}:", {k: resp.json()[k] for k in ("username", "department", "clearance")} if resp.status_code == 200 else resp.text)
    assert resp.status_code == 200

    print("\n== [3] 反例：错误 audience 被拒 ==")
    bad = _mint(aud="other-app")
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {bad}"})
    print(f"   状态 {resp.status_code}（期望 401）")
    assert resp.status_code == 401

    _server.shutdown()
    print("\nOIDC 演示全部通过 ✅（无需真实 IdP）")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\n❌ 演示失败: {exc}", file=sys.stderr)
        sys.exit(1)
