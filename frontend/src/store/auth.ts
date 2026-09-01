import { create } from "zustand";
import {
  loginApi,
  fetchMe,
  setAccessToken,
  setRefreshToken,
  restoreTokens,
  setAuthFailureHandler,
  type UserInfo,
} from "../api/client";

const TOKEN_KEY = "ek_access_token";
const REFRESH_KEY = "ek_refresh_token";
const USER_KEY = "ek_user";

// 模块加载时恢复令牌（供 API 层直接使用；access + refresh 双令牌）
restoreTokens();

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
  token: localStorage.getItem(TOKEN_KEY),
  user: readStoredUser(),

  login: async (username, password) => {
    const res = await loginApi(username, password);
    localStorage.setItem(TOKEN_KEY, res.access_token);
    localStorage.setItem(REFRESH_KEY, res.refresh_token); // 轮换制，刷新时还会再换新
    localStorage.setItem(USER_KEY, JSON.stringify(res.user));
    setAccessToken(res.access_token);
    setRefreshToken(res.refresh_token);
    set({ token: res.access_token, user: res.user });
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    setAccessToken(null);
    setRefreshToken(null);
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

// 刷新令牌失败（refresh 也失效/过期）时登出回登录页
setAuthFailureHandler(() => useAuth.getState().logout());
