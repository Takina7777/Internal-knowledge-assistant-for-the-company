"""对话路由：完整回答 + SSE 流式回答（需登录）。"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_chat_service, get_current_user
from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["对话"])


@router.post("", response_model=ChatResponse, summary="完整回答（需登录）")
def chat(
    req: ChatRequest,
    service=Depends(get_chat_service),
    _current_user: dict = Depends(get_current_user),
) -> ChatResponse:
    try:
        return service.run(req.question, req.session_id)
    except RuntimeError as exc:
        # 常见于未配置 LLM_API_KEY / Ollama 未启动，给出可读错误
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/stream", summary="SSE 流式回答（token 级打字机，需登录）")
async def chat_stream(
    req: ChatRequest,
    service=Depends(get_chat_service),
    _current_user: dict = Depends(get_current_user),
) -> EventSourceResponse:
    async def event_gen():
        async for event, payload in service.stream(req.question, req.session_id):
            yield {"data": json.dumps({"type": event, **payload}, ensure_ascii=False)}

    return EventSourceResponse(event_gen())
