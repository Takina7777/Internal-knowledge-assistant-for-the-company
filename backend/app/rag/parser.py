"""文档解析：支持 .md/.txt/.pdf/.docx，统一输出为 Markdown 风格文本。"""

from pathlib import Path

_SUPPORTED = {".md", ".markdown", ".txt", ".pdf", ".docx"}


def parse_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED:
        raise ValueError(f"暂不支持的文档格式: {suffix}（支持: {', '.join(sorted(_SUPPORTED))}）")

    if suffix in {".md", ".markdown", ".txt"}:
        return path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        import fitz  # PyMuPDF

        with fitz.open(path) as doc:
            return "\n\n".join(page.get_text("text") for page in doc)

    if suffix == ".docx":
        import docx  # python-docx

        d = docx.Document(str(path))
        return "\n\n".join(p.text for p in d.paragraphs)

    raise ValueError(f"解析器未覆盖格式: {suffix}")
