"""认证路由：登录 / 刷新令牌 / 当前用户。"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.user_store import UserStore
from app.models.schemas import LoginRequest, RefreshRequest, TokenResponse, UserInfo

router = APIRouter(prefix="/auth", tags=["认证"])
_user_store = UserStore()


@router.post("/login", response_model=TokenResponse, summary="账号密码登录")
def login(req: LoginRequest) -> TokenResponse:
    user = _user_store.authenticate(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    access_token = create_access_token(str(user["id"]))
    refresh_token = _user_store.issue_refresh_token(user["id"])
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserInfo(**user),
    )


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌（轮换）")
def refresh(req: RefreshRequest) -> TokenResponse:
    user = _user_store.consume_refresh_token(req.refresh_token)
    if not user:
        raise HTTPException(status_code=401, detail="刷新令牌无效或已过期")
    access_token = create_access_token(str(user["id"]))
    new_refresh = _user_store.issue_refresh_token(user["id"])
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=UserInfo(**user),
    )


@router.get("/me", response_model=UserInfo, summary="当前登录用户")
def me(current_user: dict = Depends(get_current_user)) -> UserInfo:
    return UserInfo(**current_user)
