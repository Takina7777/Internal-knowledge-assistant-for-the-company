"""LangGraph 节点实现：retrieve → generate → guard。

每个节点只做一件事、只返回对 State 的增量更新，便于单测与替换。
"""

import re

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.state import AgentState
from app.rag.retrieval import RetrievalService
from app.services.llm import get_llm

_retrieval = RetrievalService()

_SENSITIVE_PATTERNS: list[tuple[str, str]] = [
    (r"1[3-9]\d{9}", "手机号"),
    (r"\d{17}[\dXx]", "身份证号"),
]


def retrieve_node(state: AgentState) -> dict:
    """检索节点：向量检索（按用户 ACL 过滤）+ 组装引用信息。"""
    question = state["question"]
    results = _retrieval.search(question, user=state.get("user"))
    chunks = [
        {"text": r.chunk.text, "metadata": r.chunk.metadata, "score": r.score} for r in results
    ]
    citations = [
        {
            "index": i + 1,
            "doc_id": c["metadata"].get("doc_id", "未知"),
            "doc_name": c["metadata"].get("doc_name", "未知文档"),
            "source": c["metadata"].get("source", ""),
        }
        for i, c in enumerate(chunks)
    ]
    return {"chunks": chunks, "citations": citations}


def generate_node(state: AgentState) -> dict:
    """生成节点：基于检索片段生成带引用的回答（无检索结果时模型会拒答）。"""
    context = "\n\n".join(f"[{i + 1}] {c['text']}" for i, c in enumerate(state["chunks"]))
    prompt = SYSTEM_PROMPT.format(context=context, question=state["question"])
    answer = get_llm().invoke(prompt).content or ""
    return {"answer": answer}


def guard_node(state: AgentState) -> dict:
    """校验节点：空回答兜底 + 敏感信息脱敏。"""
    answer = (state.get("answer") or "").strip()
    if not answer:
        answer = "知识库中没有找到相关资料，建议咨询相关部门。"
    answer = _mask_sensitive(answer)
    return {"answer": answer}


def _mask_sensitive(text: str) -> str:
    for pattern, name in _SENSITIVE_PATTERNS:
        text = re.sub(pattern, f"[{name}已脱敏]", text)
    return text
