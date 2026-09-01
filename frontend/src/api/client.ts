export interface Citation {
  index: number;
  doc_id: string;
  doc_name: string;
  source: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  session_id: string;
  latency_ms: number;
}

export interface StreamEvent {
  type: "token" | "citations" | "done" | "error";
  content?: string;
  citations?: Citation[];
  session_id?: string;
  message?: string;
}

export interface UserInfo {
  id: number;
  username: string;
  display_name: string;
  role: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserInfo;
}

export interface DocumentInfo {
  doc_id: string;
  doc_name: string;
  source: string;
  status: string;
  chunk_count: number;
}

export interface TaskStatus {
  task_id: string;
  state: string;
  result: { doc_id?: string; chunks?: number } | null;
  error?: string | null;
}

// ---- 令牌管理（access + refresh 双令牌，401 自动续期） ----

const TOKEN_KEY = "ek_access_token";
const REFRESH_KEY = "ek_refresh_token";

let accessToken: string | null = null;
let refreshToken: string | null = null;
let refreshPromise: Promise<string> | null = null;
let authFailureHandler: (() => void) | null = null;

/** 模块加载时从 localStorage 恢复双令牌（auth store 初始化前调用）。 */
export function restoreTokens(): void {
  accessToken = localStorage.getItem(TOKEN_KEY);
  refreshToken = localStorage.getItem(REFRESH_KEY);
}

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function setRefreshToken(token: string | null) {
  refreshToken = token;
}

/** 注册“刷新令牌失败”回调（auth store 用它登出回登录页）。 */
export function setAuthFailureHandler(fn: () => void) {
  authFailureHandler = fn;
}

function authHeaders(): Record<string, string> {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
}

function persistTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

function clearTokens() {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function refreshAccessToken(): Promise<string> {
  if (!refreshToken) throw new Error("无刷新令牌");
  // 并发 401 只发起一次刷新，其余请求复用同一个 Promise
  if (!refreshPromise) {
    refreshPromise = fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`刷新令牌失败: ${res.status}`);
        const data = (await res.json()) as TokenResponse;
        persistTokens(data.access_token, data.refresh_token); // 轮换制：旧令牌立即失效
        return data.access_token;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

/** 统一请求入口：401 时自动用 refresh_token 换新并重试原请求一次。 */
async function apiFetch(path: string, init: RequestInit = {}, retried = false): Promise<Response> {
  const res = await fetch(path, { ...init, headers: { ...init.headers, ...authHeaders() } });
  if (res.status === 401 && !retried && refreshToken) {
    try {
      await refreshAccessToken();
    } catch {
      clearTokens();
      authFailureHandler?.();
      throw new Error("登录已失效，请重新登录");
    }
    return apiFetch(path, init, true);
  }
  return res;
}

// ---- 认证 API ----

export async function loginApi(username: string, password: string): Promise<TokenResponse> {
  // 登录接口不走 apiFetch：401 表示密码错误，不应触发令牌刷新
  const res = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? `登录失败: ${res.status}`);
  }
  return res.json();
}

export async function fetchMe(): Promise<UserInfo> {
  const res = await apiFetch("/api/v1/auth/me");
  if (!res.ok) throw new Error(`获取用户信息失败: ${res.status}`);
  return res.json();
}

// ---- 对话 API ----

export async function sendChat(question: string, sessionId?: string): Promise<ChatResponse> {
  const res = await apiFetch("/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`请求失败: ${res.status}`);
  return res.json();
}

/** SSE 流式回答：解析 sse-starlette 的 data 行（信封 {type, ...payload}） */
export async function* streamChat(
  question: string,
  sessionId?: string,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const res = await apiFetch("/api/v1/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`请求失败: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let parsed = 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // sse-starlette 按 HTTP 行尾规范用 CRLF（\r\n\r\n）分隔帧，先归一化为 \n 再切分，
    // 否则 indexOf("\n\n") 永远匹配不到 \r\n\r\n，导致一个事件都解析不出来。
    buffer = buffer.replace(/\r\n/g, "\n");

    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const line = raw.split("\n").find((l) => l.startsWith("data:"));
      if (line) {
        try {
          parsed++;
          yield JSON.parse(line.slice(5).trim()) as StreamEvent;
        } catch {
          /* 忽略非 JSON 行 */
        }
      }
    }
  }

  // 流尾可能没有结束分隔符（连接被截断）：兜底解析残留的完整 data 行
  const tail = buffer.split("\n").find((l) => l.startsWith("data:"));
  if (tail) {
    try {
      parsed++;
      yield JSON.parse(tail.slice(5).trim()) as StreamEvent;
    } catch {
      /* 忽略残缺帧 */
    }
  }

  if (parsed === 0) {
    throw new Error("服务端未返回任何数据，请确认后端服务正在运行");
  }
}

// ---- 文档 API ----

export async function uploadDocument(file: File): Promise<{ task_id: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await apiFetch("/api/v1/documents/upload", {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`上传失败: ${res.status}`);
  return res.json();
}

export async function fetchDocuments(): Promise<DocumentInfo[]> {
  const res = await apiFetch("/api/v1/documents");
  if (!res.ok) throw new Error(`获取文档列表失败: ${res.status}`);
  return res.json();
}

export async function fetchTaskStatus(taskId: string): Promise<TaskStatus> {
  const res = await apiFetch(`/api/v1/documents/tasks/${taskId}`);
  if (!res.ok) throw new Error(`查询任务失败: ${res.status}`);
  return res.json();
}
