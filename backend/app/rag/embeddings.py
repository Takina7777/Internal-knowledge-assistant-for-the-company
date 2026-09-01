"""Embedding 服务：本地 Ollama 的 bge-m3，通过 OpenAI 兼容端点 /v1/embeddings 调用。

启动前置：ollama serve 运行中，且已 `ollama pull bge-m3`。
"""

from openai import OpenAI

from app.core.config import get_settings


class EmbeddingService:
    def __init__(self) -> None:
        s = get_settings()
        # Ollama 的 OpenAI 兼容端点不校验 key，传占位符即可
        self._client = OpenAI(base_url=s.EMBEDDING_BASE_URL, api_key="ollama-local")
        self.model = s.EMBEDDING_MODEL
        self.batch_size = s.EMBEDDING_BATCH_SIZE
        self.dim = s.EMBEDDING_DIM

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量向量化（自动分批，供文档入库使用）。"""
        if not texts:
            return []
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            resp = self._client.embeddings.create(model=self.model, input=batch)
            out.extend(item.embedding for item in resp.data)
        return out

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
