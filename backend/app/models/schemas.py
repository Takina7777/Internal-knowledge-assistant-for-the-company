"""API 数据模型（Pydantic v2）。"""

from pydantic import BaseModel, Field


# ---- 对话 ----

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    session_id: str | None = Field(None, description="会话 ID；多轮对话时回传服务端返回的 session_id")


class Citation(BaseModel):
    index: int
    doc_id: str
    doc_name: str
    source: str = ""


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    session_id: str
    latency_ms: int = 0


# ---- 认证 ----

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: str = ""
    role: str = "user"


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserInfo


# ---- 文档 / 任务 ----

class UploadResponse(BaseModel):
    task_id: str
    doc_id: str
    filename: str
    status: str = "queued"


class DocumentInfo(BaseModel):
    doc_id: str
    doc_name: str = ""
    source: str = ""
    status: str = ""
    chunk_count: int = 0


class TaskStatus(BaseModel):
    task_id: str
    state: str  # PENDING | STARTED | SUCCESS | FAILURE | ...
    result: dict | None = None
    error: str | None = None
