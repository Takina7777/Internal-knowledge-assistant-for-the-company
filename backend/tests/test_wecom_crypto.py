"""企业微信 WXBizMsgCrypt 单元测试：官方样例向量（URL 验证）+ 往返 + 签名校验。

官方样例来自企业微信开发者文档「加解密方案说明」（https://developer.work.weixin.qq.com/document/path/90968）：
  GET /wecom/callback?msg_signature=5c45ff5e21c57e6ad56bac8758b79b1d9ac89fd3
     &timestamp=1409659589&nonce=263014780&echostr=P9nAzCzyDtyTWESHep1vC5X9xho%2FqYX3Zpb4yKa9SKld1DsH3Iyt3tP3zNdtp%2B4RPcs8TgAE7OaBO%2BFZXvnaqQ%3D%3D
"""

import pytest

from app.wecom.crypto import WXBizMsgCrypt, WXBizMsgCryptError

TOKEN = "QDG6eK"
AES_KEY = "jWmYm7qr5nMoAUwZRjGtBxmz3KA1tkAj3ykkR6q2B2C"
RECEIVE_ID = "wx5823bf96d3bd56c7"

# 官方 URL 验证样例
SIGNATURE = "5c45ff5e21c57e6ad56bac8758b79b1d9ac89fd3"
TIMESTAMP = "1409659589"
NONCE = "263014780"
ENCRYPT_ECHOSTR = "P9nAzCzyDtyTWESHep1vC5X9xho/qYX3Zpb4yKa9SKld1DsH3Iyt3tP3zNdtp+4RPcs8TgAE7OaBO+FZXvnaqQ=="
PLAIN_ECHOSTR = "1616140317555161061"


def _crypt() -> WXBizMsgCrypt:
    return WXBizMsgCrypt(TOKEN, AES_KEY, RECEIVE_ID)


def test_signature_matches_official_vector():
    crypt = _crypt()
    sig = crypt.get_signature(TOKEN, TIMESTAMP, NONCE, ENCRYPT_ECHOSTR)
    assert sig == SIGNATURE
    assert crypt.verify_signature(SIGNATURE, TIMESTAMP, NONCE, ENCRYPT_ECHOSTR)


def test_url_verification_official_vector():
    crypt = _crypt()
    assert crypt.verify_url(SIGNATURE, TIMESTAMP, NONCE, ENCRYPT_ECHOSTR) == PLAIN_ECHOSTR


def test_encrypt_decrypt_roundtrip():
    crypt = _crypt()
    msg = "<xml><ToUserName>toUser</ToUserName><Content>你好，知知</Content></xml>"
    encrypt, sig = crypt.encrypt(msg, NONCE, TIMESTAMP)
    assert crypt.decrypt(encrypt, sig, TIMESTAMP, NONCE) == msg


def test_bad_signature_rejected():
    crypt = _crypt()
    with pytest.raises(WXBizMsgCryptError):
        crypt.decrypt(ENCRYPT_ECHOSTR, "0" * 40, TIMESTAMP, NONCE)


def test_wrong_receive_id_rejected():
    other = WXBizMsgCrypt(TOKEN, AES_KEY, "wx-other")
    msg = "hello"
    encrypt, sig = other.encrypt(msg, NONCE, TIMESTAMP)
    with pytest.raises(WXBizMsgCryptError):
        _crypt().decrypt(encrypt, sig, TIMESTAMP, NONCE)


def test_aes_key_length_validation():
    with pytest.raises(WXBizMsgCryptError):
        WXBizMsgCrypt(TOKEN, "too-short", RECEIVE_ID)
