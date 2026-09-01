"""企业微信回调路由（不需要 JWT，由企业微信服务器调用）。

- GET  /wecom/callback   后台配置回调 URL 时的验证（验签 + 解密 echostr）
- POST /wecom/callback   接收消息：解密 → 解析 → 异步调 Agent → 5 秒内回 success

配置：WECOM_CORP_ID / WECOM_AGENT_ID / WECOM_SECRET / WECOM_TOKEN / WECOM_AES_KEY（backend/.env）。
"""

import xml.etree.ElementTree as ET

from fastapi import APIRouter, HTTPException, Request, Response

from app.core.config import get_settings
from app.services import chat as chat_service
from app.wecom.client import WeComClient
from app.wecom.crypto import WXBizMsgCrypt, WXBizMsgCryptError
from app.wecom.handler import WeComHandler, parse_message

router = APIRouter(prefix="/wecom", tags=["企业微信"])

_handler_instance: WeComHandler | None = None


def _crypt() -> WXBizMsgCrypt:
    s = get_settings()
    if not (s.WECOM_TOKEN and s.WECOM_AES_KEY and s.WECOM_CORP_ID):
        raise HTTPException(status_code=503, detail="企业微信未配置（WECOM_CORP_ID / WECOM_TOKEN / WECOM_AES_KEY）")
    return WXBizMsgCrypt(s.WECOM_TOKEN, s.WECOM_AES_KEY, s.WECOM_CORP_ID)


def _handler() -> WeComHandler:
    """单例 handler：复用 access_token 缓存；agent_fn 同步调 LangGraph run。"""
    global _handler_instance
    if _handler_instance is None:

        def agent(question: str) -> str:
            return chat_service.run(question).answer

        _handler_instance = WeComHandler(client=WeComClient(), agent_fn=agent)
    return _handler_instance


@router.get("/callback", summary="企业微信回调 URL 验证")
def verify_url(timestamp: str, nonce: str, echostr: str, msg_signature: str) -> Response:
    try:
        plain = _crypt().verify_url(msg_signature, timestamp, nonce, echostr)
    except WXBizMsgCryptError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=plain, media_type="text/plain")


@router.post("/callback", summary="接收企业微信消息（文本触发 Agent）")
async def receive(request: Request) -> Response:
    query = request.query_params
    timestamp = query.get("timestamp", "")
    nonce = query.get("nonce", "")
    msg_signature = query.get("msg_signature", "")
    body = await request.body()

    try:
        xml_text = _crypt().decrypt(body.decode("utf-8"), msg_signature, timestamp, nonce)
        msg = parse_message(xml_text)
    except (WXBizMsgCryptError, ET.ParseError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _handler().handle(msg)  # 后台异步处理，5 秒内先回 success
    return Response(content="success", media_type="text/plain")
