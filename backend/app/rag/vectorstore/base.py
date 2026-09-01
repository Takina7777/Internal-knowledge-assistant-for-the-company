"""向量存储抽象层。

Phase 1 用 Chroma（零运维）；Phase 2 数据量上来后可平滑切换到 Qdrant：
实现 QdrantStore 并设置 VECTOR_STORE_BACKEND=qdrant 即可，业务代码零改动。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """一个待入库/已入库的文档块。"""

    id: str
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ScoredChunk:
    """带相似度分数的检索结果。"""

    chunk: Chunk
    score: float


class VectorStore(ABC):
    @abstractmethod
    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """批量写入（embedding 由外部计算好传入，保持后端无关）。"""

    @abstractmethod
    def search(
        self, query_vector: list[float], top_k: int = 5, where: dict | None = None
    ) -> list[ScoredChunk]:
        """向量检索；where 为元数据过滤条件（权限过滤在此扩展）。"""

    @abstractmethod
    def delete(self, ids: list[str]) -> None: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def list_documents(self) -> list[dict]:
        """按 doc_id 汇总已入库文档信息。"""
