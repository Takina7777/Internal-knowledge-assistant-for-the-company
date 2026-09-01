"""FastAPI 应用入口。

启动：cd backend && .venv\\Scripts\\python -m uvicorn app.main:app --reload --port 8000
文档：http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, chat, documents, health
from app.core.config import get_settings
from app.wecom import routes as wecom_routes

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="0.3.0",
    description="企业内部知识助手后端：LangGraph + DeepSeek(OpenAI 兼容) + Ollama bge-m3 + Chroma + JWT/OIDC 认证 + ACL + 企业微信",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(chat.router, prefix=settings.API_PREFIX)
app.include_router(documents.router, prefix=settings.API_PREFIX)
app.include_router(wecom_routes.router, prefix=settings.API_PREFIX)


@app.get("/")
def root() -> dict:
    return {
        "app": settings.APP_NAME,
        "version": "0.2.0",
        "docs": "/docs",
        "api_prefix": settings.API_PREFIX,
        "vector_store": settings.VECTOR_STORE_BACKEND,
        "auth_provider": settings.AUTH_PROVIDER,
    }
