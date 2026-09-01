"""异步任务：文档接入管道（解析 → 分块 → 向量化 → 入库），幂等可重试。"""

from datetime import datetime
from pathlib import Path

from app.rag.chunker import split_markdown
from app.rag.embeddings import EmbeddingService
from app.rag.parser import parse_file
from app.rag.vectorstore import get_vector_store
from app.rag.vectorstore.base import Chunk
from app.workers.celery_app import celery_app


@celery_app.task(name="ingest_document", bind=True, max_retries=3, default_retry_delay=5)
def ingest_document(
    self,
    doc_id: str,
    file_path: str,
    doc_name: str = "",
    source: str = "",
) -> dict:
    """单篇文档入库；失败自动重试（最多 3 次）。"""
    try:
        text = parse_file(Path(file_path))
        items = split_markdown(text)

        chunks = [
            Chunk(
                id=f"{doc_id}::{i}",
                text=item.text,
                metadata={
                    **item.metadata,
                    "doc_id": doc_id,
                    "doc_name": doc_name or Path(file_path).name,
                    "source": source,
                    "ingested_at": datetime.now().isoformat(),
                },
            )
            for i, item in enumerate(items)
        ]

        embeddings = EmbeddingService().embed_texts([c.text for c in chunks])

        store = get_vector_store()
        store.delete([c.id for c in chunks])  # 幂等：重跑前清掉旧版本
        store.add(chunks, embeddings)

        return {"doc_id": doc_id, "chunks": len(chunks)}
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc) from exc
