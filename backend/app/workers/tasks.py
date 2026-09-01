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
    department: str = "",
    clearance: int = 0,
) -> dict:
    """单篇文档入库；失败自动重试（最多 3 次）。

    department：允许访问的部门（空 = 全员可读）；clearance：所需最低密级（0-5）。
    """
    try:
        text = parse_file(Path(file_path))
        items = split_markdown(text)

        # ACL 元数据：department 非空时写入 acl_departments（Chroma 元数据支持 list），
        # clearance 非 0 时写入 acl_clearance；缺失即视为全员可读（向后兼容老文档）。
        acl_meta: dict = {}
        if department:
            acl_meta["acl_departments"] = [department]
        if clearance:
            acl_meta["acl_clearance"] = int(clearance)

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
                    **acl_meta,
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
