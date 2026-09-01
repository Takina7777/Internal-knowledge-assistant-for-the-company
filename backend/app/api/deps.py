"""依赖注入：配置、服务单例、当前用户（JWT）。

SSO/OIDC 预留：定义 AuthProvider 抽象（Protocol），默认 JwtAuthProvider；
对接公司 IdP（Keycloak / ADFS / 自建 SSO）时实现 OidcAuthProvider，
并把 AUTH_PROVIDER 切换为 oidc 即可，业务代码零改动。
"""

from typing import Protocol

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
    """SSO/OIDC 认证（Phase 2）：对接公司 IdP 后实现本类。"""

    def __init__(self) -> None:
        raise NotImplementedError(
            "Phase 2：接入公司 SSO/OIDC（Keycloak/ADFS/自建）后实现，"
            "并将 AUTH_PROVIDER 切换为 oidc。"
        )

    def authenticate(self, token: str) -> dict | None:  # pragma: no cover
        raise NotImplementedError


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
