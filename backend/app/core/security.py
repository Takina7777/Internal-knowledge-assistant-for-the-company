"""安全工具：密码哈希（bcrypt）与 JWT 令牌（pyjwt）。"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings


def hash_password(plain: str) -> str:
    """bcrypt 哈希（自动加盐）。"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    """签发 access token（JWT HS256）。subject 为用户 ID。"""
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=s.JWT_ACCESS_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, s.JWT_SECRET, algorithm=s.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """校验并解析 JWT；失败返回 None（不抛异常）。"""
    s = get_settings()
    try:
        return jwt.decode(token, s.JWT_SECRET, algorithms=[s.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
