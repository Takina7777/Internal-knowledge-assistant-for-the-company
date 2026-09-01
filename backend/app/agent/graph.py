"""Agent 主图：retrieve → generate → guard（线性流水线，预留条件边扩展）。

扩展方向（Phase 2）：
  - intent 节点：意图识别/路由（知识问答 / 闲聊 / 工具调用）
  - 工具调用节点：ConditionalEdge 分派
  - 人审闸门：高风险动作挂起等待人工审批
"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph

from app.agent.nodes import generate_node, guard_node, retrieve_node
from app.agent.state import AgentState


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.add_node("guard", guard_node)

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "guard")
    g.add_edge("guard", END)

    # InMemorySaver：进程内会话记忆（thread_id 隔离会话）。
    # 生产环境建议替换为 PostgresSaver / SqliteSaver（langgraph-checkpoint-postgres 等）。
    return g.compile(checkpointer=InMemorySaver())
