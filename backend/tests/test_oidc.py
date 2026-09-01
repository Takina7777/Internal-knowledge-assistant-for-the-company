"""OIDC 认证单元测试：RS256 ID Token + JWKS 校验（使用本地生成的密钥，不依赖真实 IdP）。"""

import base64
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.api.deps import OidcAuthProvider

ISSUER = "https://sso.example.com/realms/ek"
CLIENT_ID = "ek-web"
KID = "test-key-1"


def _b64u_int(i: int) -> str:
    length = (i.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(i.to_bytes(length, "big")).rstrip(b"=").decode()


def _make_jwks(private_key) -> dict:
    nums = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": KID,
        "use": "sig",
        "alg": "RS256",
        "n": _b64u_int(nums.n),
        "e": _b64u_int(nums.e),
    }
    return {"keys": [jwk]}


def _mint_token(private_key, **overrides) -> str:
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


@pytest.fixture(scope="module")
def private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _provider(private_key, **kwargs) -> OidcAuthProvider:
    return OidcAuthProvider(jwks=_make_jwks(private_key), issuer=ISSUER, client_id=CLIENT_ID, **kwargs)


def test_valid_id_token_authenticates(private_key):
    provider = _provider(private_key)
    user = provider.authenticate(_mint_token(private_key))
    assert user is not None
    assert user["id"] == "u-1001"
    assert user["username"] == "zhangsan"
    assert user["display_name"] == "张三"
    assert user["department"] == "hr"
    assert user["clearance"] == 3


def test_wrong_audience_rejected(private_key):
    provider = _provider(private_key)
    assert provider.authenticate(_mint_token(private_key, aud="other-app")) is None


def test_wrong_issuer_rejected(private_key):
    provider = _provider(private_key)
    assert provider.authenticate(_mint_token(private_key, iss="https://evil.example.com")) is None


def test_expired_token_rejected(private_key):
    provider = _provider(private_key)
    token = _mint_token(private_key, exp=int(time.time()) - 100)
    assert provider.authenticate(token) is None


def test_tampered_token_rejected(private_key):
    provider = _provider(private_key)
    token = _mint_token(private_key)
    tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    assert provider.authenticate(tampered) is None


def test_missing_kid_rejected(private_key):
    provider = _provider(private_key)
    claims = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "sub": "u-1",
        "iat": int(time.time()),
        "exp": int(time.time()) + 600,
    }
    token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "unknown-kid"})
    assert provider.authenticate(token) is None
