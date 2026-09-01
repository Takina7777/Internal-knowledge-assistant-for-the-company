import { create } from "zustand";
import { loginApi, fetchMe, setAccessToken, type UserInfo } from "../api/client";

const TOKEN_KEY = "ek_access_token";
const USER_KEY = "ek_user";

function readStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

// 模块加载时恢复令牌（供 API 层直接使用）
const initialToken = readStoredToken();
setAccessToken(initialToken);

function readStoredUser(): UserInfo | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserInfo;
  } catch {
    return null;
  }
}

interface AuthState {
  token: string | null;
  user: UserInfo | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  token: initialToken,
  user: readStoredUser(),

  login: async (username, password) => {
    const res = await loginApi(username, password);
    localStorage.setItem(TOKEN_KEY, res.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify(res.user));
    setAccessToken(res.access_token);
    set({ token: res.access_token, user: res.user });
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setAccessToken(null);
    set({ token: null, user: null });
  },

  refreshUser: async () => {
    try {
      const user = await fetchMe();
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      set({ user });
    } catch {
      // token 失效，交由页面跳转登录处理
      useAuth.getState().logout();
    }
  },
}));
