"""可观测性抽象接口。

Phase 1 使用 noop（仅预留接口）；Phase 2 部署 Langfuse 自托管后：
  1. 实现 LangfuseTracer；
  2. 设置 OBSERVABILITY_PROVIDER=langfuse 并填写 LANGFUSE_* 配置。
"""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager, nullcontext
from typing import Any

from app.core.config import get_settings


class Tracer(ABC):
    """链路追踪抽象：所有可观测入口统一走这里。"""

    @abstractmethod
    def span(self, name: str, **attrs: Any) -> AbstractContextManager[Any]: ...


class NoopTracer(Tracer):
    """空实现：零开销，Phase 1 默认。"""

    def span(self, name: str, **attrs: Any) -> AbstractContextManager[Any]:
        return nullcontext()


class LangfuseTracer(Tracer):
    """Langfuse 自托管实现（Phase 2）。"""

    def __init__(self) -> None:
        raise NotImplementedError(
            "Phase 2：接入 Langfuse 自托管（参考 docker-compose 部署 Langfuse）后实现本类。"
        )

    def span(self, name: str, **attrs: Any) -> AbstractContextManager[Any]:
        raise NotImplementedError


def get_tracer() -> Tracer:
    settings = get_settings()
    if settings.OBSERVABILITY_PROVIDER == "langfuse":
        return LangfuseTracer()
    return NoopTracer()
