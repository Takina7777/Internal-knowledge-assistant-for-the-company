"""ACL 检索权限过滤单元测试。"""

from app.rag.acl import can_access, filter_scored
from app.rag.vectorstore.base import Chunk, ScoredChunk


def _scored(meta: dict, score: float = 0.9) -> ScoredChunk:
    return ScoredChunk(Chunk(id="c1", text="t", metadata=meta), score)


def test_open_doc_anyone_can_access():
    assert can_access({}, {"department": "hr", "clearance": 0})
    assert can_access({"acl_departments": [], "acl_clearance": 0}, {"department": "tech", "clearance": 1})


def test_department_restricted():
    meta = {"acl_departments": ["hr"]}
    assert can_access(meta, {"department": "hr", "clearance": 1})
    assert not can_access(meta, {"department": "tech", "clearance": 5})


def test_clearance_restricted():
    meta = {"acl_clearance": 3}
    assert can_access(meta, {"department": "x", "clearance": 3})
    assert not can_access(meta, {"department": "x", "clearance": 2})


def test_admin_bypasses_acl():
    meta = {"acl_departments": ["hr"], "acl_clearance": 5}
    assert can_access(meta, {"role": "admin"})


def test_filter_scored_keeps_order():
    open_chunk = _scored({"acl_clearance": 1}, 0.9)
    hr_chunk = _scored({"acl_departments": ["hr"]}, 0.8)
    top_chunk = _scored({"acl_clearance": 4}, 0.7)
    chunks = [open_chunk, hr_chunk, top_chunk]
    user = {"department": "hr", "clearance": 2}
    result = filter_scored(chunks, user)
    assert result == [open_chunk, hr_chunk]
