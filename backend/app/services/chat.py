"""对话服务：编排 LangGraph 图，提供完整回答与 SSE 流式回答。

流式实现：graph.astream(stream_mode=["updates", "messages"])
  - updates 模式：节点级事件（retrieve 产出引用）
  - messages 模式：LLM token 级事件（打字机效果）
"""

import time
import uuid
from typing import AsyncIterator

from langchain_core.messages import AIMessageChunk

from app.agent.graph import build_graph
from app.models.schemas import ChatResponse, Citation

_graph = build_graph()


def run(question: str, session_id: str | None = None, user: dict | None = None) -> ChatResponse:
    """完整回答（非流式）。"""
    session_id = session_id or uuid.uuid4().hex
    start = time.perf_counter()
    result = _graph.invoke(
        {"question": question, "user": user}, config={"configurable": {"thread_id": session_id}}
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    citations = [Citation(**c) for c in result.get("citations", [])]
    return ChatResponse(
        answer=result.get("answer", ""),
        citations=citations,
        session_id=session_id,
        latency_ms=latency_ms,
    )


async def stream(
    question: str,
    session_id: str | None = None,
    user: dict | None = None,
) -> AsyncIterator[tuple[str, dict]]:
    """流式回答，产出 (event, payload)：
    - ("citations", {...}) 检索完成后的引用列表
    - ("token", {"content": str}) 增量 token
    - ("done", {...}) 结束（含最终引用与 session_id）
    - ("error", {"message": str}) 出错
    """
    session_id = session_id or uuid.uuid4().hex
    citations: list[dict] = []
    try:
        async for mode, data in _graph.astream(
            {"question": question, "user": user},
            config={"configurable": {"thread_id": session_id}},
            stream_mode=["updates", "messages"],
        ):
            if mode == "updates":
                for node_name, payload in data.items():
                    if node_name == "retrieve" and payload.get("citations"):
                        citations = payload["citations"]
                        yield "citations", {"citations": citations}
            elif mode == "messages":
                msg = data[0] if isinstance(data, tuple) else data
                if isinstance(msg, AIMessageChunk) and msg.content:
                    yield "token", {"content": msg.content}
        yield "done", {"session_id": session_id, "citations": citations}
    except Exception as exc:  # noqa: BLE001 - 流式场景向客户端返回错误事件
        yield "error", {"message": str(exc)}
