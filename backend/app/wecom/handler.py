"""企业微信消息处理：XML 解析 → 调 Agent → 5 秒内先回 success，结果异步推送。

流程：
  1. POST /wecom/callback 收到加密 XML → crypto.decrypt 得到明文
  2. parse_message 解析出 MsgType / Content / FromUserName
  3. handle() 起后台线程调 agent_fn（同步调 LangGraph run），立即返回空串（<5s）
  4. 后台线程把回答通过 WeComClient.send_text 推给用户
"""

import threading
import xml.etree.ElementTree as ET
from typing import Callable

from app.wecom.client import WeComClient


def parse_message(xml_text: str) -> dict:
    """解析企业微信回调明文 XML 为 dict（未知标签原样保留）。"""
    root = ET.fromstring(xml_text)
    return {child.tag: (child.text or "").strip() for child in root}


class WeComHandler:
    def __init__(
        self,
        client: WeComClient | None = None,
        agent_fn: Callable[[str], str] | None = None,
    ) -> None:
        """agent_fn: 输入问题文本，输出回答文本（同步；内部走 LangGraph run）。"""
        self.client = client or WeComClient()
        self.agent_fn = agent_fn

    def handle(self, msg: dict) -> str:
        """处理一条消息；同步返回空串（保证 5 秒内响应），结果异步推送。"""
        if msg.get("MsgType") != "text" or not msg.get("Content"):
            return ""
        user = msg.get("FromUserName", "")
        question = msg["Content"].strip()
        threading.Thread(target=self._async_answer, args=(user, question), daemon=True).start()
        return ""

    def _async_answer(self, user: str, question: str) -> None:
        try:
            answer = self.agent_fn(question) if self.agent_fn else "知识库服务未就绪。"
            self.client.send_text(user, answer)
        except Exception as exc:  # noqa: BLE001
            try:
                self.client.send_text(user, f"处理失败：{exc}")
            except Exception:  # noqa: BLE001 - 推送失败仅记录，不抛到请求线程
                pass
