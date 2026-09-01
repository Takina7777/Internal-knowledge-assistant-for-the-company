"""Celery 应用：broker/backend 均使用 Redis。"""

from celery import Celery

from app.core.config import get_settings

s = get_settings()

celery_app = Celery(
    "enterprise_knowledge_agent",
    broker=s.CELERY_BROKER_URL,
    backend=s.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
)

# 显式导入任务模块以完成注册（worker 启动时才会识别 ingest_document 等任务）
from app.workers import tasks as _tasks  # noqa: E402,F401


def _patch_kombu_mutex_for_fakeredis() -> None:
    """开发环境适配：fakeredis（内存 Redis）不支持 Lua/EVALSHA，
    而 kombu 的 redis 传输用 Lua 脚本实现未确认消息互斥锁（Mutex）。
    单 worker 开发场景退化为无锁；多 worker / 生产环境必须使用真实 Redis
    并保持 CELERY_DEV_NO_LUA=false。"""
    import kombu.transport.redis as kombu_redis

    class _NoopMutex:
        def __init__(self, client, name, expire) -> None:  # noqa: ANN001
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc) -> bool:  # noqa: ANN002
            return False

    kombu_redis.Mutex = _NoopMutex


if s.CELERY_DEV_NO_LUA:
    _patch_kombu_mutex_for_fakeredis()
