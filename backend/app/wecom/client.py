"""企业微信 API 客户端：access_token 缓存 + 主动发消息。

依赖配置（backend/.env）：WECOM_CORP_ID / WECOM_SECRET / WECOM_AGENT_ID。
"""

import time

import httpx

from app.core.config import get_settings

_QYAPI = "https://qyapi.weixin.qq.com/cgi-bin"


class WeComClient:
    def __init__(self, corpid: str | None = None, secret: str | None = None, agent_id: str | None = None) -> None:
        s = get_settings()
        self.corpid = corpid or s.WECOM_CORP_ID
        self.secret = secret or s.WECOM_SECRET
        self.agent_id = agent_id or s.WECOM_AGENT_ID
        self._token = ""
        self._token_expires_at = 0.0

    def get_access_token(self) -> str:
        """获取 access_token（进程内缓存，提前 60s 刷新）。"""
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        resp = httpx.get(
            f"{_QYAPI}/gettoken",
            params={"corpid": self.corpid, "corpsecret": self.secret},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("errcode") != 0:
            raise RuntimeError(f"获取 access_token 失败: {data}")
        self._token = data["access_token"]
        self._token_expires_at = time.time() + int(data.get("expires_in", 7200))
        return self._token

    def send_text(self, to_user: str, content: str) -> dict:
        """给指定用户（FromUserName）发送文本消息。"""
        if not self.agent_id:
            raise RuntimeError("未配置 WECOM_AGENT_ID")
        resp = httpx.post(
            f"{_QYAPI}/message/send",
            params={"access_token": self.get_access_token()},
            json={
                "touser": to_user,
                "msgtype": "text",
                "agentid": int(self.agent_id),
                "text": {"content": content},
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("errcode") != 0:
            raise RuntimeError(f"发送消息失败: {data}")
        return data
