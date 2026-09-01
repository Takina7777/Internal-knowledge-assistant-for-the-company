"""Chroma 实现（Phase 1 默认向量库，本地持久化，零运维）。"""

import uuid

import chromadb

from app.core.config import get_settings
from app.rag.vectorstore.base import Chunk, ScoredChunk, VectorStore


class ChromaStore(VectorStore):
    def __init__(self) -> None:
        s = get_settings()
        self._client = chromadb.PersistentClient(path=s.CHROMA_PERSIST_DIR)
        self._collection = self._client.get_or_create_collection(
            name=s.CHROMA_COLLECTION, metadata={"hnsw:space": "cosine"}
        )

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        ids = [c.id or str(uuid.uuid4()) for c in chunks]
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
        )

    def search(
        self, query_vector: list[float], top_k: int = 5, where: dict | None = None
    ) -> list[ScoredChunk]:
        total = self._collection.count()
        if total == 0:
            return []
        res = self._collection.query(
            query_embeddings=[query_vector],
            n_results=min(top_k, total),
            where=where,  # 权限过滤等元数据条件
        )
        out: list[ScoredChunk] = []
        for i, doc_id in enumerate(res["ids"][0]):
            metadata = (res["metadatas"][0] or [{}])[i] or {}
            out.append(
                ScoredChunk(
                    chunk=Chunk(id=doc_id, text=res["documents"][0][i], metadata=metadata),
                    score=1.0 - res["distances"][0][i],  # cosine 距离转相似度
                )
            )
        return out

    def delete(self, ids: list[str]) -> None:
        if ids:
            self._collection.delete(ids=ids)

    def count(self) -> int:
        return self._collection.count()

    def list_documents(self) -> list[dict]:
        got = self._collection.get(include=["metadatas"])
        docs: dict[str, dict] = {}
        for meta in got.get("metadatas") or []:
            if not meta:
                continue
            doc_id = meta.get("doc_id", "unknown")
            docs.setdefault(doc_id, meta)
        return [{"doc_id": k, **v} for k, v in docs.items()]
