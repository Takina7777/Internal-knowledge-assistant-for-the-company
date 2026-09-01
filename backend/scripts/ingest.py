"""本地文档批量入库（开发用，同步执行，无需 Celery/Redis）。

用法（在 backend 目录下）：
    .venv\\Scripts\\python scripts\\ingest.py --path ../docs
    .venv\\Scripts\\python scripts\\ingest.py --path ../docs/示例_公司年假制度.md
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# 保证从任意目录运行时都能 import app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Windows 控制台默认 GBK，强制 UTF-8 输出避免 emoji/中文编码报错
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

from app.rag.chunker import split_markdown
from app.rag.embeddings import EmbeddingService
from app.rag.parser import parse_file
from app.rag.vectorstore import get_vector_store
from app.rag.vectorstore.base import Chunk

SUPPORTED = {".md", ".markdown", ".txt", ".pdf", ".docx"}


def ingest_file(path: Path) -> int:
    text = parse_file(path)
    items = split_markdown(text)

    doc_id = path.stem
    chunks = [
        Chunk(
            id=f"{doc_id}::{i}",
            text=item.text,
            metadata={
                **item.metadata,
                "doc_id": doc_id,
                "doc_name": path.name,
                "source": str(path),
                "ingested_at": datetime.now().isoformat(),
            },
        )
        for i, item in enumerate(items)
    ]

    embeddings = EmbeddingService().embed_texts([c.text for c in chunks])

    store = get_vector_store()
    store.delete([c.id for c in chunks])  # 幂等：重跑先清旧
    store.add(chunks, embeddings)
    return len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="本地文档批量入库（同步）")
    parser.add_argument("--path", required=True, help="文档目录或单个文件")
    args = parser.parse_args()

    p = Path(args.path)
    files = [p] if p.is_file() else [f for f in p.rglob("*") if f.suffix.lower() in SUPPORTED]

    if not files:
        print("没有找到支持的文档（md/txt/pdf/docx）")
        return

    total = 0
    for f in files:
        try:
            n = ingest_file(f)
            total += n
            print(f"  ✓ {f.name}: {n} 块")
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ {f.name}: {exc}")

    print(f"\n完成：共 {len(files)} 篇文档，入库 {total} 块。")


if __name__ == "__main__":
    main()
