"""检索权限过滤（ACL）：按用户部门 + 密级过滤检索结果，实现"检索不到=答不出来"。

文档块元数据约定（入库时写入，见 workers/tasks.py / scripts/ingest.py）：
  - acl_departments: list[str]  允许访问的部门；缺失/空 = 全员可读
  - acl_clearance: int          所需最低密级（0-5）；缺失/0 = 全员可读

用户上下文约定（来自 JWT/OIDC 的用户信息）：
  - department: str  用户部门
  - clearance: int   用户密级（0-5）
  - role: str        用户角色；role == "admin" 时绕过 ACL
"""

from app.rag.vectorstore.base import ScoredChunk


def can_access(meta: dict, user: dict | None) -> bool:
    """判断某文档块元数据对当前用户是否可见。"""
    if not user:
        # 内部调用（脚本/冒烟测试）不限制；公开接口总是携带用户上下文
        return True
    if user.get("role") == "admin":
        return True
    allowed = meta.get("acl_departments") or []
    min_clearance = int(meta.get("acl_clearance") or 0)
    user_dept = user.get("department") or ""
    user_clearance = int(user.get("clearance") or 0)
    if allowed and user_dept not in allowed:
        return False
    if min_clearance > user_clearance:
        return False
    return True


def filter_scored(chunks: list[ScoredChunk], user: dict | None) -> list[ScoredChunk]:
    """按用户 ACL 过滤带分数的检索结果（保持原有顺序）。"""
    return [c for c in chunks if can_access(c.chunk.metadata, user)]
