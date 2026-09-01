"""检索服务：查询向量化 → 向量检索。

Phase 2 扩展点：
  - 混合检索（BM25 + 向量融合）
  - Rerank 重排（bge-reranker 或云端 rerank API）
  - 权限过滤（where 条件注入用户 ACL）
"""

from app.core.config import get_settings
from app.rag.embeddings import EmbeddingService
from app.rag.vectorstore import get_vector_store
from app.rag.vectorstore.base import ScoredChunk


class RetrievalService:
    def __init__(self) -> None:
        self.embeddings = EmbeddingService()
        self.store = get_vector_store()
        self.top_k = get_settings().RETRIEVE_TOP_K

    def search(self, query: str, top_k: int | None = None, where: dict | None = None) -> list[ScoredChunk]:
        query_vector = self.embeddings.embed_query(query)
        return self.store.search(query_vector, top_k=top_k or self.top_k, where=where)
