"""分块策略：优先按 Markdown 标题层级切小节，小节内按段落聚合到目标长度，带重叠。

Phase 2 可升级为 parent-child（子块检索、父块生成）或按语义切分。
"""

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)


@dataclass
class ChunkItem:
    text: str
    metadata: dict


def split_markdown(text: str, chunk_size: int = 800, overlap: int = 100) -> list[ChunkItem]:
    """将 Markdown 文本切分为带小节标题元数据的块。"""
    matches = list(_HEADING_RE.finditer(text))
    sections: list[tuple[str, str]] = []
    if not matches:
        sections.append(("", text))
    else:
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections.append((m.group(2).strip(), text[m.start() : end]))

    items: list[ChunkItem] = []
    for title, body in sections:
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", body) if p.strip()]
        buf: list[str] = []
        buf_len = 0
        for para in paragraphs:
            if buf and buf_len + len(para) > chunk_size:
                items.append(_make_item(title, buf))
                tail = "\n".join(buf)[-overlap:] if overlap > 0 else ""
                buf, buf_len = ([tail] if tail else [], len(tail))
            buf.append(para)
            buf_len += len(para) + 1
        if buf:
            items.append(_make_item(title, buf))
    return items


def _make_item(title: str, paragraphs: list[str]) -> ChunkItem:
    return ChunkItem(
        text="\n".join(paragraphs),
        metadata={"title": title or "未命名小节"},
    )
