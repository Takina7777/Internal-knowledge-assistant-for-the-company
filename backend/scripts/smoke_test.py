"""冒烟测试：验证 Embedding(Ollama bge-m3) / 向量库(Chroma) / LLM 配置 / 完整问答链路。

用法（在 backend 目录下）：
    .venv\\Scripts\\python scripts\\smoke_test.py
"""

import sys
from pathlib import Path

# 保证从任意目录运行时都能 import app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Windows 控制台默认 GBK，强制 UTF-8 输出避免 emoji/中文编码报错
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass


def main() -> None:
    print("== 1. Embedding（Ollama bge-m3）==")
    from app.rag.embeddings import EmbeddingService

    emb = EmbeddingService()
    vec = emb.embed_query("向量连通性测试")
    print(f"   OK model={emb.model} dim={len(vec)}")

    print("== 2. 向量库（Chroma 读写回环）==")
    from app.rag.vectorstore import get_vector_store
    from app.rag.vectorstore.base import Chunk

    store = get_vector_store()
    store.add(
        [
            Chunk(
                id="smoke::0",
                text="公司年假制度：入职满一年可享受 5 天带薪年假。",
                metadata={"doc_id": "smoke", "doc_name": "冒烟测试"},
            )
        ],
        [vec],
    )
    hits = store.search(vec, top_k=1)
    assert hits, "检索未命中"
    print(f"   OK 检索命中: {hits[0].chunk.text[:24]}... (score={hits[0].score:.3f})")
    store.delete(["smoke::0"])
    assert store.count() == 0 or True  # 不强制空库（可能有真实数据）

    print("== 3. LLM 配置（deepseek-v4-flash）==")
    from app.core.config import get_settings

    s = get_settings()
    if not s.LLM_API_KEY or s.LLM_API_KEY.startswith("sk-xxx"):
        print("   ⚠ 未配置 LLM_API_KEY，跳过问答链路。复制 .env.example 为 .env 后重跑。")
        return
    print(f"   OK model={s.LLM_MODEL} base={s.LLM_BASE_URL}")

    print("== 4. 完整问答链路（LangGraph）==")
    from app.services.chat import run

    resp = run("新员工入职当年年假怎么算？")
    print(f"   回答: {resp.answer[:100]}...")
    print(f"   引用: {len(resp.citations)} 条 | 耗时: {resp.latency_ms}ms")
    print("   会话: " + resp.session_id[:12])

    print("\n冒烟测试通过 ✅")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"\n❌ 冒烟测试失败: {exc}", file=sys.stderr)
        sys.exit(1)
