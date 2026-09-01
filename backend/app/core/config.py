"""应用配置：全部来自环境变量 / backend/.env（pydantic-settings）。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录（本文件位于 backend/app/core/config.py）
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # 无论从哪个工作目录启动，都固定读取 backend/.env（环境变量优先级更高）
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- LLM（deepseek-v4-flash，OpenAI 兼容接口）----
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_API_KEY: str = ""  # 必填，见 backend/.env
    LLM_MODEL: str = "deepseek-v4-flash"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2048

    # ---- Embedding（本地 Ollama bge-m3，OpenAI 兼容端点 /v1/embeddings）----
    EMBEDDING_BASE_URL: str = "http://localhost:11434/v1"
    EMBEDDING_MODEL: str = "bge-m3"
    EMBEDDING_DIM: int = 1024  # bge-m3 输出维度
    EMBEDDING_BATCH_SIZE: int = 32

    # ---- 向量库（chroma | qdrant）----
    VECTOR_STORE_BACKEND: str = "chroma"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION: str = "knowledge_docs"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "knowledge_docs"

    # ---- Redis / Celery ----
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    # 开发环境（fakeredis 内存 Redis）不支持 Lua/EVALSHA，置 true 时给 kombu
    # 未确认消息互斥锁打无锁补丁（仅适合单 worker 开发；真实 Redis 必须为 false）
    CELERY_DEV_NO_LUA: bool = False

    # ---- 可观测（noop | langfuse，Phase 2 自托管 Langfuse）----
    OBSERVABILITY_PROVIDER: str = "noop"
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "http://localhost:3000"

    # ---- 认证（JWT + 本地账号；AUTH_PROVIDER=oidc 时为 SSO/OIDC）----
    AUTH_PROVIDER: str = "jwt"  # jwt | oidc
    JWT_SECRET: str = "dev-only-secret-change-in-production"  # 生产环境必须替换
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_EXPIRE_DAYS: int = 7
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"  # 首次启动自动创建管理员，请务必修改
    DB_PATH: str = "./data/app.db"  # SQLite（相对 backend/ 目录）

    # ---- SSO/OIDC（AUTH_PROVIDER=oidc 时启用）----
    OIDC_ISSUER: str = ""  # IdP issuer，如 https://sso.example.com/realms/ek
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_JWKS_URI: str = ""  # 可选；缺省从 issuer 的 .well-known/openid-configuration 自动发现
    OIDC_ID_TOKEN_ALG: str = "RS256"

    # ---- 检索权限过滤（ACL：部门 + 密级）----
    ADMIN_DEPARTMENT: str = ""  # 管理员部门（空 = 全部部门可访问）
    ADMIN_CLEARANCE: int = 5  # 管理员密级（0-5，5 最高）
    ACL_FETCH_MULTIPLIER: int = 3  # 预取倍数：ACL 过滤后仍能保证 Top-K

    # ---- 企业微信（Phase 2 接入，先留配置占位）----
    WECOM_CORP_ID: str = ""
    WECOM_AGENT_ID: str = ""
    WECOM_SECRET: str = ""
    WECOM_TOKEN: str = ""
    WECOM_AES_KEY: str = ""

    # ---- 应用 ----
    APP_NAME: str = "企业知识内部助手"
    API_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    RETRIEVE_TOP_K: int = 5
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    UPLOAD_DIR: str = "./data/uploads"


@lru_cache
def get_settings() -> Settings:
    """全局配置单例（lru_cache 保证只解析一次）。"""
    return Settings()
