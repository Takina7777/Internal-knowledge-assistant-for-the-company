"""开发用内存 Redis（fakeredis TCP 服务器）。

无 Docker 环境下的 Redis 替代品（数据不持久化，仅限开发环境使用）。
生产环境请使用真实 Redis（参考根目录 docker-compose.yml）。

用法（backend 目录下）：
    .venv\\Scripts\\python scripts\\dev_redis.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

import fakeredis  # noqa: E402

# fakeredis 2.37 的 TCP 服务器硬编码 Resp3Writer（RESP3 空值为 "_"），
# kombu/celery 的 redis 客户端按 RESP2 解析会在 BRPOP 超时等空值场景崩掉。
# 开发脚本强制改用 Resp2Writer（"-1" 表示空值），与 redis-py/kombu 兼容。
import fakeredis._tcp_server as _frs  # noqa: E402

_frs.Resp3Writer = _frs.Resp2Writer

HOST, PORT = "127.0.0.1", 6379


def main() -> None:
    server = fakeredis.TcpFakeServer((HOST, PORT))
    print(f"[dev-redis] 已启动 {HOST}:{PORT}（fakeredis 内存模式，不持久化，Ctrl+C 退出）")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[dev-redis] 已停止")


if __name__ == "__main__":
    main()
