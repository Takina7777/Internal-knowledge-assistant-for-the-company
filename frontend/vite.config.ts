import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // 开发环境把 /api 代理到 FastAPI 后端（显式 IPv4，避免 localhost→::1 解析歧义）
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
