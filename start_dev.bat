@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo   企业知识内部助手 - 一键启动（3 个窗口）
echo   后端 :8000  |  Celery Worker  |  前端 :5173
echo ============================================

REM 1) 后端 API
start "后端API :8000" cmd /k "cd /d %~dp0backend && .venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

REM 2) Celery Worker（文档上传入库用）
start "CeleryWorker" cmd /k "cd /d %~dp0backend && .venv\Scripts\python -m celery -A app.workers.celery_app.celery_app worker --pool=solo --loglevel=INFO"

REM 3) 前端
start "前端 :5173" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo 已启动 3 个窗口，等待 3~5 秒后访问 http://localhost:5173
echo 关闭对应窗口即可停止对应服务。
timeout /t 3 >nul
