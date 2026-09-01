"""文档路由：上传接入（异步 Celery 任务）+ 任务状态 + 已入库列表（均需登录）。"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.models.schemas import DocumentInfo, TaskStatus, UploadResponse
from app.rag.vectorstore import get_vector_store
from app.workers.tasks import ingest_document

router = APIRouter(prefix="/documents", tags=["文档管理"])


@router.post("/upload", response_model=UploadResponse, summary="上传文档并异步入库（需登录）")
async def upload(
    file: UploadFile = File(...),
    _current_user: dict = Depends(get_current_user),
) -> UploadResponse:
    s = get_settings()
    upload_dir = Path(s.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    doc_id = uuid.uuid4().hex
    filename = file.filename or "untitled"
    path = upload_dir / f"{doc_id}_{filename}"
    path.write_bytes(await file.read())

    task = ingest_document.delay(
        doc_id=doc_id,
        file_path=str(path),
        doc_name=filename,
        source="upload",
    )
    return UploadResponse(task_id=task.id, doc_id=doc_id, filename=filename)


@router.get("/tasks/{task_id}", response_model=TaskStatus, summary="查询入库任务状态（需登录）")
def task_status(
    task_id: str,
    _current_user: dict = Depends(get_current_user),
) -> TaskStatus:
    from app.workers.celery_app import celery_app

    res = celery_app.AsyncResult(task_id)
    return TaskStatus(
        task_id=task_id,
        state=res.state,
        result=res.result if res.successful() else None,
        error=str(res.traceback)[:2000] if res.failed() else None,
    )


@router.get("", response_model=list[DocumentInfo], summary="已入库文档列表（需登录）")
def list_documents(
    _current_user: dict = Depends(get_current_user),
) -> list[DocumentInfo]:
    store = get_vector_store()
    return [DocumentInfo(**item) for item in store.list_documents()]
