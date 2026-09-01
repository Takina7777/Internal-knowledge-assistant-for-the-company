# 企业知识内部助手

基于 **LangGraph** 的企业内部知识问答系统（Phase 1 骨架 + Phase 2 基础能力）。

- **问答模型**：deepseek-v4-flash（OpenAI 兼容 API，`backend/.env` 配置）
- **向量模型**：本地 Ollama `bge-m3:latest`（无需 GPU 推理服务，Ollama 即可）
- **编排**：LangGraph（retrieve → generate → guard 状态机，支持 token 级流式）
- **向量库**：Chroma（本地持久化）；预留 Qdrant 抽象层可平滑切换
- **异步管道**：Celery + Redis（文档上传异步入库 + 任务状态轮询）
- **认证**：JWT + 本地账号（bcrypt + pyjwt），预留 SSO/OIDC 适配接口
- **可观测**：抽象接口已预留（noop / Langfuse）
- **前端**：React 18 + TypeScript + Vite + Ant Design（登录 / 智能问答 / 文档管理）

## 目录结构

```
企业知识内部助手/
├── docs/                     # 示例知识文档（用于验证检索链路）
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── core/             # 配置 / 安全(JWT+bcrypt) / 可观测抽象
│   │   ├── db/               # SQLite 用户存储（refresh token 轮换）
│   │   ├── agent/            # LangGraph 状态机（state / nodes / graph / prompts）
│   │   ├── rag/              # embeddings / chunker / parser / retrieval / vectorstore
│   │   ├── services/         # LLM 封装 / 对话编排（含流式）
│   │   ├── api/routes/       # health / auth / chat / documents / wecom(占位)
│   │   ├── models/           # Pydantic 数据模型
│   │   ├── wecom/            # 企业微信（Phase 2，配置占位）
│   │   └── workers/          # Celery 应用与文档接入任务
│   ├── scripts/              # ingest / smoke_test / dev_redis（fakeredis 开发替代）
│   ├── tests/                # pytest（含认证测试）
│   ├── requirements.txt      # 运行依赖
│   ├── requirements-dev.txt  # 开发/测试依赖（含 fakeredis）
│   └── .env.example          # 复制为 .env 后填写
├── frontend/                 # React + Vite 门户（登录/问答/文档管理）
├── docker-compose.yml        # Redis（必）+ Qdrant（可选，--profile qdrant）
└── README.md
```

## 快速开始

### 前置条件

- Python 3.13（本机已装 `D:\Python3.13`）
- Ollama 已运行且已拉取模型：`ollama pull bge-m3`
- Redis：Docker（推荐）或开发期 fakeredis（见下文「Redis 方案」）
- Node.js ≥ 20

### 1. 启动 Redis

**方式 A：真实 Redis（推荐，生产一致）**

```bash
cd 企业知识内部助手
docker compose up -d          # 仅 Redis；需要 Qdrant 时: docker compose --profile qdrant up -d
```

**方式 B：开发期 fakeredis（无 Docker 时，内存模式不持久化）**

```bash
cd backend
.venv\Scripts\python scripts\dev_redis.py          # 启动内存 Redis(127.0.0.1:6379)
# 并把 backend/.env 中 CELERY_DEV_NO_LUA 置为 true（fakeredis 不支持 Lua 的兼容开关）
```

### 2. 后端

```bash
cd backend
py -3.13 -m venv .venv                                        # 若 sandbox 环境 ensurepip 失败，见下方【备注】
.venv\Scripts\python -m pip install -r requirements-dev.txt
copy .env.example .env                                        # 填写 LLM_API_KEY、JWT_SECRET、ADMIN_PASSWORD 等
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

- 交互文档：http://localhost:8000/docs
- 首次启动自动创建管理员账号（`ADMIN_USERNAME` / `ADMIN_PASSWORD`，见 `.env`，请立即修改）

### 3. Celery worker（文档上传异步入库时需要）

```bash
cd backend
.venv\Scripts\python -m celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

> Windows 下如遇进程问题，加 `--pool=solo`。

### 4. 前端

```bash
cd frontend
npm install
npm run dev                  # http://localhost:5173（/api 已代理到 8000）
```

打开后用管理员账号登录，即可使用「智能问答」和「文档管理」。

### 5. 冒烟验证

```bash
cd backend
.venv\Scripts\python scripts\smoke_test.py
```

## 配置说明（backend/.env）

| 配置项 | 说明 | 默认 |
|---|---|---|
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | deepseek-v4-flash 的 OpenAI 兼容端点 | 必填 |
| `EMBEDDING_BASE_URL` / `EMBEDDING_MODEL` | Ollama OpenAI 兼容端点 | `http://localhost:11434/v1` / `bge-m3` |
| `VECTOR_STORE_BACKEND` | 向量库后端 | `chroma`（`qdrant` 为 Phase 2） |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis 地址 | `redis://localhost:6379/0`、`/1` |
| `CELERY_DEV_NO_LUA` | fakeredis 开发模式的 kombu 兼容开关 | `false`（fakeredis 时 `true`） |
| `AUTH_PROVIDER` | 认证方式 | `jwt`（`oidc` 为 Phase 2 SSO） |
| `JWT_SECRET` | JWT 签名密钥（生产必须换成随机长串） | dev 默认值 |
| `JWT_ACCESS_EXPIRE_MINUTES` / `JWT_REFRESH_EXPIRE_DAYS` | 令牌有效期 | `120` / `7` |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 首次启动自动创建的管理员 | `admin` / 请在 .env 修改 |
| `DB_PATH` | SQLite 用户库路径（相对 backend/） | `./data/app.db` |
| `WECOM_*` | 企业微信凭证（Phase 2 占位） | 空 |
| `OBSERVABILITY_PROVIDER` | 可观测实现 | `noop`（`langfuse` 为 Phase 2） |
| `RETRIEVE_TOP_K` / `CHUNK_SIZE` / `CHUNK_OVERLAP` | 检索与分块参数 | `5` / `800` / `100` |

## API 一览（前缀 /api/v1，除 health 外均需 `Authorization: Bearer <token>`）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/login` | 账号密码登录，返回 access + refresh token |
| POST | `/auth/refresh` | 刷新令牌（轮换制，旧令牌立即失效） |
| GET | `/auth/me` | 当前登录用户 |
| POST | `/chat` | 完整回答 |
| POST | `/chat/stream` | SSE 流式回答（token 级） |
| POST | `/documents/upload` | 上传文档，Celery 异步入库 |
| GET | `/documents/tasks/{task_id}` | 入库任务状态（PENDING/STARTED/SUCCESS/FAILURE） |
| GET | `/documents` | 已入库文档列表 |
| GET | `/health` | 服务健康 |
| GET | `/health/embedding` | Ollama bge-m3 连通性 |

## 认证说明

- **登录流程**：`POST /auth/login` → 前端保存 token（localStorage）→ 请求头携带 `Authorization: Bearer <access_token>`。
- **刷新**：access token 默认 2h 过期；`POST /auth/refresh` 轮换 refresh token（服务端哈希存储、单次有效）。
- **SSO/OIDC（Phase 2）**：`app/api/deps.py` 定义了 `AuthProvider` 抽象；对接公司 IdP 时实现
  `OidcAuthProvider` 并把 `AUTH_PROVIDER=oidc`，业务代码零改动。
- **权限过滤**：检索链路（`retrieve` 节点的 `where` 条件）接入用户 ACL 属于 Phase 2 内容。

## 企业微信机器人（Phase 2，暂缓实现）

已预留配置占位（`WECOM_CORP_ID` / `WECOM_AGENT_ID` / `WECOM_SECRET` / `WECOM_TOKEN` / `WECOM_AES_KEY`）
与模块骨架（`app/wecom/`，见其 docstring）。启用时需：

1. 企业微信管理后台创建「自建应用」，获取 corpid / agentid / secret；
2. 配置消息接收回调 URL（公网 HTTPS）+ 随机 Token / EncodingAESKey；
3. 按 `app/wecom/__init__.py` 的规划实现 `crypto.py`（官方 AES 加解密）、`client.py`（主动发消息）、
   `handler.py`（消息 → agent → 5 秒内回 success，结果异步推送），并挂载回调路由。

## 升级路径（Phase 2 预埋）

- **向量库 Chroma → Qdrant**：实现 `app/rag/vectorstore/qdrant_store.py`（协议在 `base.py`），改 `VECTOR_STORE_BACKEND=qdrant`，业务零改动。
- **认证 → SSO/OIDC**：实现 `app/api/deps.py` 的 `OidcAuthProvider`，改 `AUTH_PROVIDER=oidc`。
- **可观测 → Langfuse 自托管**：实现 `app/core/observability.py` 的 `LangfuseTracer`，改 `OBSERVABILITY_PROVIDER=langfuse`。
- **会话记忆**：`build_graph()` 当前用 `InMemorySaver`，生产换 `PostgresSaver`/`SqliteSaver`。
- **检索增强**：混合检索（BM25+向量）、Rerank 重排（见 `app/rag/retrieval.py` 注释）。
- **用户库 SQLite → PostgreSQL**：替换 `app/db/user_store.py` 实现，接口不变。

## 备注：沙箱环境（DSH）下的已知问题与处理

本机 DSH 文件沙箱对子进程有两条限制，本项目已内置规避方案：

1. **ensurepip / pip 临时目录清理失败（WinError 5）**
   沙箱禁止子进程 `os.chmod`；CPython 在 Windows 上把 `os.mkdir(mode!=0o777)`
   映射为只读属性，导致 tempfile 的 0o700 临时目录无法删除。
   规避（已写入 venv 的 `sitecustomize.py`，仅 Windows 生效）：
   `os.mkdir` 忽略 mode 参数，临时目录以默认属性创建。

2. **Node 子进程 spawn 被拒（EPERM）**
   沙箱禁止"带管道 stdio 的子进程 spawn"，esbuild（Vite 依赖）必然触发。
   规避：`npm run dev` / `npm run build` 需在沙箱外执行或授权全权限运行；
   `npm install` 已用 `--ignore-scripts` 正常完成。

> venv 属于本机环境（已 gitignore），换机器重装时按上述第 1 条补丁即可。
> fakeredis 兼容补丁说明：真实 Redis 不支持时（`CELERY_DEV_NO_LUA=true`）会禁用 kombu
> 的 Lua 互斥锁（仅适合单 worker 开发）；生产环境必须用真实 Redis 且保持该开关为 `false`。
