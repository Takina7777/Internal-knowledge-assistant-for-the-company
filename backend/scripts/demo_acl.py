"""检索权限 ACL 无真实环境演示：临时 Chroma 入库一篇"公开"和一篇"hr 密级3"文档，
用不同用户身份检索，验证部门/密级过滤与 admin 绕过（不污染真实知识库）。

用法（在 backend 目录下，需本机 Ollama 已运行 bge-m3）：
    .venv\\Scripts\\python scripts\\demo_acl.py
预期：
    hr/密级3   -> 命中 2 条（公开 + 薪酬）
    tech/密级1 -> 命中 1 条（仅公开）
    admin      -> 命中 2 条（绕过 ACL）
"""

import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

# 使用临时 Chroma，避免污染真实知识库（必须在 import app.rag.* 之前设置）
_tmp = tempfile.mkdtemp(prefix="ek_acl_demo_")
os.environ["CHROMA_PERSIST_DIR"] = os.path.join(_tmp, "chroma")
os.environ["CHROMA_COLLECTION"] = "demo_knowledge"

from app.rag.chunker import split_markdown  # noqa: E402
from app.rag.embeddings import EmbeddingService  # noqa: E402
from app.rag.retrieval import RetrievalService  # noqa: E402
from app.rag.vectorstore import get_vector_store  # noqa: E402
from app.rag.vectorstore.base import Chunk  # noqa: E402


def ingest(text: str, doc_id: str, department: str = "", clearance: int = 0) -> None:
    items = split_markdown(text)
    acl: dict = {}
    if department:
        acl["acl_departments"] = [department]
    if clearance:
        acl["acl_clearance"] = clearance
    chunks = [
        Chunk(
            id=f"{doc_id}::{i}",
            text=item.text,
            metadata={
                **item.metadata,
                "doc_id": doc_id,
                "doc_name": f"{doc_id}.md",
                "source": "demo",
                "ingested_at": datetime.now().isoformat(),
                **acl,
            },
        )
        for i, item in enumerate(items)
    ]
    emb = EmbeddingService().embed_texts([c.text for c in chunks])
    store = get_vector_store()
    store.delete([c.id for c in chunks])
    store.add(chunks, emb)


def main() -> None:
    print("== 入库 2 篇演示文档 ==")
    ingest("公司年假制度：入职满一年可享受 5 天带薪年假，满 5 年 10 天。", "公开制度")
    ingest("薪酬保密：核心绩效奖金方案属于 hr 部门高密级文档，不得外传。", "薪酬方案", department="hr", clearance=3)
    print("   ✓ 公开制度（无限制）")
    print("   ✓ 薪酬方案（hr 部门 / 密级3）")

    rs = RetrievalService()

    def show(label: str, user: dict | None) -> None:
        hits = rs.search("薪酬 奖金 年假", user=user)
        names = [h.chunk.metadata.get("doc_id") for h in hits]
        print(f"   {label}: 命中 {len(hits)} 条 -> {names}")
        return hits

    print("\n== 不同身份检索「薪酬 奖金 年假」==")
    hits_hr = show("hr/密级3 ", {"department": "hr", "clearance": 3})
    hits_tech = show("tech/密级1", {"department": "tech", "clearance": 1})
    hits_admin = show("admin     ", {"role": "admin"})

    assert len(hits_hr) == 2 and "薪酬方案" in [h.chunk.metadata.get("doc_id") for h in hits_hr], "hr 应命中 2 条"
    assert len(hits_tech) == 1, "tech/密级1 应只命中公开文档"
    assert len(hits_admin) == 2, "admin 应绕过 ACL 命中 2 条"

    shutil.rmtree(_tmp, ignore_errors=True)
    print("\nACL 演示全部通过 ✅（未污染真实知识库）")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(_tmp, ignore_errors=True)
        print(f"\n❌ 演示失败: {exc}", file=sys.stderr)
        sys.exit(1)
