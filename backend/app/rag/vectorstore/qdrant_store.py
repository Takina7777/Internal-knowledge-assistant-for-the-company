"""Qdrant 实现（Phase 2 迁移目标）。

启用步骤：
  1. docker compose --profile qdrant up -d
  2. 实现本类（参考 base.VectorStore 协议与 ChromaStore 的用法）
  3. 设置 VECTOR_STORE_BACKEND=qdrant

业务代码无需改动——这正是抽象层存在的意义。
"""

from app.rag.vectorstore.base import Chunk, ScoredChunk, VectorStore


class QdrantStore(VectorStore):
    def __init__(self) -> None:
        raise NotImplementedError(
            "Qdrant 适配计划在 Phase 2 实现；当前请使用 Chroma（VECTOR_STORE_BACKEND=chroma）。"
        )

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        raise NotImplementedError

    def search(
        self, query_vector: list[float], top_k: int = 5, where: dict | None = None
    ) -> list[ScoredChunk]:
        raise NotImplementedError

    def delete(self, ids: list[str]) -> None:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError

    def list_documents(self) -> list[dict]:
        raise NotImplementedError
