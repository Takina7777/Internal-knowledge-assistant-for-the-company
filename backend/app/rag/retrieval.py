"""检索服务：查询向量化 → 向量检索 → ACL 权限过滤。

Phase 2 扩展点：
  - 混合检索（BM25 + 向量融合）
  - Rerank 重排（bge-reranker 或云端 rerank API）
  - 权限过滤（按用户部门/密级过滤，见 app/rag/acl.py）
"""

from app.core.config import get_settings
from app.rag import acl
from app.rag.embeddings import EmbeddingService
from app.rag.vectorstore import get_vector_store
from app.rag.vectorstore.base import ScoredChunk


class RetrievalService:
    def __init__(self) -> None:
        self.embeddings = EmbeddingService()
        self.store = get_vector_store()
        self.top_k = get_settings().RETRIEVE_TOP_K
        self.acl_multiplier = get_settings().ACL_FETCH_MULTIPLIER

    def search(
        self,
        query: str,
        user: dict | None = None,
        top_k: int | None = None,
        where: dict | None = None,
    ) -> list[ScoredChunk]:
        """检索并过滤 ACL。user 为 None 时不限制（内部调用）。"""
        k = top_k or self.top_k
        query_vector = self.embeddings.embed_query(query)
        # 先多取 ACL_FETCH_MULTIPLIER 倍，过滤后仍能保证 Top-K
        fetched = self.store.search(query_vector, top_k=k * self.acl_multiplier, where=where)
        filtered = acl.filter_scored(fetched, user)
        return filtered[:k]
