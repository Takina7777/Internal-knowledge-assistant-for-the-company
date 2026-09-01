"""分块器单元测试。"""

from app.rag.chunker import split_markdown


def test_split_markdown_follows_headings():
    text = (
        "# 标题一\n\n第一段内容。\n\n第二段内容。\n\n"
        "## 小节\n\n更多内容。"
    )
    items = split_markdown(text, chunk_size=50, overlap=0)
    assert len(items) >= 2
    assert all(item.text for item in items)
    assert any("标题一" in item.metadata["title"] for item in items)


def test_split_markdown_with_overlap():
    text = "段落A。\n\n段落B。\n\n段落C。" + "长文本" * 200
    items = split_markdown(text, chunk_size=300, overlap=50)
    assert len(items) >= 2
    # 相邻块应有重叠内容
    assert items[0].text[-50:] in items[1].text
