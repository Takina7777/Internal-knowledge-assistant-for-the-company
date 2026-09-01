"""依赖注入：配置、服务单例、当前用户（JWT / OIDC）。

AuthProvider 抽象：默认 JwtAuthProvider（本地账号）；切换 AUTH_PROVIDER=oidc
并配置 OIDC_ISSUER / OIDC_CLIENT_ID 即可接入公司 IdP（Keycloak / ADFS / 自建），
业务代码零改动。
"""

from typing import Protocol

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import Settings, get_settings
from app.core.security import decode_token
from app.db.user_store import UserStore
from app.services import chat as chat_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
_user_store = UserStore()


class AuthProvider(Protocol):
    """认证抽象：输入令牌，输出用户信息（None 表示无效）。"""

    def authenticate(self, token: str) -> dict | None: ...


class JwtAuthProvider:
    """JWT + 本地账号（当前默认认证方式）。"""

    def authenticate(self, token: str) -> dict | None:
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        try:
            user = _user_store.get_by_id(int(payload["sub"]))
        except (TypeError, ValueError):
            return None
        return user if user and user.get("is_active", True) else None


class OidcAuthProvider:
    """SSO/OIDC 认证：校验 IdP 签发的 ID Token（JWT + JWKS，默认 RS256）。

    流程：取 token 头的 kid → 拉取 JWKS（OIDC_JWKS_URI 或从 issuer 自动发现）
    → 用对应公钥校验签名/iss/aud/exp → 映射为用户信息（sub/name/role/department/clearance）。
    """

    def __init__(
        self,
        settings: Settings | None = None,
        jwks: dict | None = None,  # 测试注入，生产走网络发现
        issuer: str | None = None,
        client_id: str | None = None,
        algorithm: str | None = None,
    ) -> None:
        s = settings or get_settings()
        self.issuer = (issuer or s.OIDC_ISSUER or "").rstrip("/")
        self.client_id = client_id or s.OIDC_CLIENT_ID
        self.algorithm = algorithm or s.OIDC_ID_TOKEN_ALG
        self._jwks_uri = s.OIDC_JWKS_URI
        self._jwks = jwks

    def _discover_jwks_uri(self) -> str:
        if self._jwks_uri:
            return self._jwks_uri
        if not self.issuer:
            raise RuntimeError("未配置 OIDC_ISSUER")
        resp = httpx.get(f"{self.issuer}/.well-known/openid-configuration", timeout=10)
        resp.raise_for_status()
        return resp.json()["jwks_uri"]

    def _fetch_jwks(self) -> dict:
        if self._jwks:
            return self._jwks
        resp = httpx.get(self._discover_jwks_uri(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def authenticate(self, token: str) -> dict | None:
        try:
            kid = jwt.get_unverified_header(token).get("kid")
            jwks = self._fetch_jwks()
            jwk = next(k for k in jwks.get("keys", []) if k.get("kid") == kid)
            payload = jwt.decode(
                token,
                key=jwt.PyJWK(jwk).key,
                algorithms=[self.algorithm],
                audience=self.client_id,
                issuer=self.issuer,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except Exception:  # noqa: BLE001 - 任何校验失败一律视为未登录
            return None
        return {
            "id": payload.get("sub"),
            "username": payload.get("preferred_username") or payload.get("sub", ""),
            "display_name": payload.get("name", ""),
            "role": payload.get("role", "user"),
            "department": payload.get("department", ""),
            "clearance": int(payload.get("clearance") or 0),
            "is_active": True,
        }


def get_auth_provider() -> AuthProvider:
    settings = get_settings()
    if settings.AUTH_PROVIDER == "oidc":
        return OidcAuthProvider()
    return JwtAuthProvider()


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    provider: AuthProvider = Depends(get_auth_provider),
) -> dict:
    """受保护路由的当前用户依赖（未登录/失效 → 401）。"""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    user = provider.authenticate(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")
    return user


def get_settings_dep() -> Settings:
    return get_settings()


def get_chat_service():
    return chat_service
