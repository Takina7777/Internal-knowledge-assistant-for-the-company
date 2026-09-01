"""健康检查路由。"""

from fastapi import APIRouter

from app.core.config import get_settings
from app.rag.embeddings import EmbeddingService

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "app": s.APP_NAME,
        "version": "0.1.0",
        "vector_store": s.VECTOR_STORE_BACKEND,
        "llm_model": s.LLM_MODEL,
        "embedding_model": s.EMBEDDING_MODEL,
    }


@router.get("/embedding")
def embedding_health() -> dict:
    """验证 Ollama bge-m3 是否可用（会实际调用一次向量化）。"""
    try:
        emb = EmbeddingService()
        vec = emb.embed_query("连通性测试")
        return {"status": "ok", "model": emb.model, "dim": len(vec)}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc)}
