"""企业微信回调加解密：WXBizMsgCrypt（官方算法）。

- AES-256-CBC + PKCS7；密钥 = base64(EncodingAESKey + "=") 的前 32 字节，IV = 密钥前 16 字节
- 密文结构：random(16B) | msg_len(4B 大端) | msg | receive_id
- 消息签名：sha1(排序后 token/timestamp/nonce/encrypt 拼接)

用法：
    crypt = WXBizMsgCrypt(token, encoding_aes_key, receive_id)
    plain = crypt.decrypt(encrypt, msg_signature, timestamp, nonce)   # 接收消息
    encrypt, msg_signature = crypt.encrypt(reply_xml, nonce, timestamp)  # 回复消息
"""

import base64
import hashlib
import hmac
import os
import struct
import time

from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class WXBizMsgCryptError(Exception):
    """加解密/验签失败。"""


class WXBizMsgCrypt:
    def __init__(self, token: str, encoding_aes_key: str, receive_id: str) -> None:
        if len(encoding_aes_key) != 43:
            raise WXBizMsgCryptError("EncodingAESKey 长度必须为 43")
        self.token = token
        self.receive_id = receive_id
        self.aes_key = base64.b64decode(encoding_aes_key + "=")
        self.aes_iv = self.aes_key[:16]

    # ---- 签名 ----

    @staticmethod
    def get_signature(token: str, timestamp: str, nonce: str, encrypt: str) -> str:
        sort_list = sorted([token, timestamp, nonce, encrypt])
        return hashlib.sha1("".join(sort_list).encode("utf-8")).hexdigest()

    def verify_signature(self, msg_signature: str, timestamp: str, nonce: str, encrypt: str) -> bool:
        return hmac.compare_digest(
            self.get_signature(self.token, timestamp, nonce, encrypt), msg_signature
        )

    # ---- AES ----

    def _aes_encrypt(self, raw: bytes) -> bytes:
        padder = sym_padding.PKCS7(128).padder()
        padded = padder.update(raw) + padder.finalize()
        encryptor = Cipher(algorithms.AES(self.aes_key), modes.CBC(self.aes_iv)).encryptor()
        return encryptor.update(padded) + encryptor.finalize()

    def _aes_decrypt(self, enc: bytes) -> bytes:
        decryptor = Cipher(algorithms.AES(self.aes_key), modes.CBC(self.aes_iv)).decryptor()
        padded = decryptor.update(enc) + decryptor.finalize()
        unpadder = sym_padding.PKCS7(128).unpadder()
        return unpadder.update(padded) + unpadder.finalize()

    # ---- 加解密 ----

    def encrypt(self, msg: str, nonce: str, timestamp: str | None = None) -> tuple[str, str]:
        """加密明文（企业微信回复用），返回 (encrypt, msg_signature)。"""
        timestamp = timestamp or str(int(time.time()))
        msg_bytes = msg.encode("utf-8")
        raw = os.urandom(16) + struct.pack(">I", len(msg_bytes)) + msg_bytes + self.receive_id.encode("utf-8")
        encrypt = base64.b64encode(self._aes_encrypt(raw)).decode("utf-8")
        return encrypt, self.get_signature(self.token, timestamp, nonce, encrypt)

    def decrypt(self, encrypt: str, msg_signature: str, timestamp: str, nonce: str) -> str:
        """验签并解密，返回明文 XML；签名不符/结构非法抛 WXBizMsgCryptError。"""
        if not self.verify_signature(msg_signature, timestamp, nonce, encrypt):
            raise WXBizMsgCryptError("消息签名校验失败")
        try:
            raw = self._aes_decrypt(base64.b64decode(encrypt))
        except Exception as exc:  # noqa: BLE001
            raise WXBizMsgCryptError(f"AES 解密失败: {exc}") from exc
        if len(raw) < 20:
            raise WXBizMsgCryptError("密文长度非法")
        msg_len = struct.unpack(">I", raw[16:20])[0]
        msg = raw[20 : 20 + msg_len].decode("utf-8")
        receive_id = raw[20 + msg_len :].decode("utf-8")
        if receive_id != self.receive_id:
            raise WXBizMsgCryptError(f"receive_id 不匹配: {receive_id!r} != {self.receive_id!r}")
        return msg

    # ---- URL 验证（GET 回调）----

    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """校验并解密 echostr，返回明文（用于企业微信后台的 URL 验证）。"""
        return self.decrypt(echostr, msg_signature, timestamp, nonce)
