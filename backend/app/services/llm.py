"""LLM 服务：deepseek-v4-flash，OpenAI 兼容接口。

统一封装 ChatOpenAI（langchain-openai），支持 LangGraph 流式（stream_mode="messages"）
与工具绑定（Phase 2 加 tools 时在 node 内 bind_tools 即可）。
"""

from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.core.config import get_settings


@lru_cache
def get_llm() -> ChatOpenAI:
    s = get_settings()
    if not s.LLM_API_KEY or s.LLM_API_KEY.startswith("sk-xxx"):
        raise RuntimeError(
            "未配置 LLM_API_KEY：请复制 backend/.env.example 为 backend/.env 并填写 deepseek-v4-flash 的 API Key。"
        )
    return ChatOpenAI(
        base_url=s.LLM_BASE_URL,
        api_key=s.LLM_API_KEY,
        model=s.LLM_MODEL,
        temperature=s.LLM_TEMPERATURE,
        max_tokens=s.LLM_MAX_TOKENS,
    )
