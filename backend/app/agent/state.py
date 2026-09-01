"""LangGraph 状态定义：Agent 全链路共享的数据结构。"""

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    question: str
    chunks: list[dict]       # 检索到的文档块（含 text/metadata/score）
    citations: list[dict]    # 引用列表（index/doc_id/doc_name/source）
    answer: str              # 最终回答
    messages: list[Any]      # 对话历史（多轮记忆预留）
