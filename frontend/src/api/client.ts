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

// ---- 令牌管理（供 auth store 写入） ----

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

function authHeaders(): Record<string, string> {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
}

// ---- 认证 API ----

export async function loginApi(username: string, password: string): Promise<TokenResponse> {
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
  const res = await fetch("/api/v1/auth/me", { headers: authHeaders() });
  if (!res.ok) throw new Error(`获取用户信息失败: ${res.status}`);
  return res.json();
}

// ---- 对话 API ----

export async function sendChat(question: string, sessionId?: string): Promise<ChatResponse> {
  const res = await fetch("/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
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
  const res = await fetch("/api/v1/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ question, session_id: sessionId }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`请求失败: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const line = raw.split("\n").find((l) => l.startsWith("data:"));
      if (line) {
        try {
          yield JSON.parse(line.slice(5).trim()) as StreamEvent;
        } catch {
          /* 忽略非 JSON 行 */
        }
      }
    }
  }
}

// ---- 文档 API ----

export async function uploadDocument(file: File): Promise<{ task_id: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/v1/documents/upload", {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) throw new Error(`上传失败: ${res.status}`);
  return res.json();
}

export async function fetchDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch("/api/v1/documents", { headers: authHeaders() });
  if (!res.ok) throw new Error(`获取文档列表失败: ${res.status}`);
  return res.json();
}

export async function fetchTaskStatus(taskId: string): Promise<TaskStatus> {
  const res = await fetch(`/api/v1/documents/tasks/${taskId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`查询任务失败: ${res.status}`);
  return res.json();
}
