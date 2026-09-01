"""向量库工厂：按配置返回后端实现（单例）。"""

from functools import lru_cache

from app.core.config import get_settings
from app.rag.vectorstore.base import VectorStore
from app.rag.vectorstore.chroma_store import ChromaStore
from app.rag.vectorstore.qdrant_store import QdrantStore


@lru_cache
def get_vector_store() -> VectorStore:
    backend = get_settings().VECTOR_STORE_BACKEND.lower()
    if backend == "chroma":
        return ChromaStore()
    if backend == "qdrant":
        return QdrantStore()
    raise ValueError(f"未知的向量库后端: {backend}（可选: chroma | qdrant）")
