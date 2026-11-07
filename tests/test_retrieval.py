from owasp_rag.retrieval import rrf_merge
from owasp_rag.schemas import Chunk


def c(cid: str) -> Chunk:
    return Chunk(id=cid, doc="d", heading="", text=cid)


def ids(chunks: list[Chunk]) -> list[str]:
    return [x.id for x in chunks]


def test_rrf_rewards_chunks_both_lists_agree_on():
    # a: 1/61 + 1/62, c: 1/63 + 1/61, b: 1/62, d: 1/63
    merged = rrf_merge([[c("a"), c("b"), c("c")], [c("c"), c("a"), c("d")]])
    assert ids(merged) == ["a", "c", "b", "d"]


def test_rrf_ties_keep_first_appearance_order():
    assert ids(rrf_merge([[c("x")], [c("y")]])) == ["x", "y"]


def test_rrf_returns_each_chunk_once():
    assert ids(rrf_merge([[c("a"), c("b")], [c("b"), c("a")]])) == ["a", "b"]


def test_rrf_empty():
    assert rrf_merge([]) == []
    assert rrf_merge([[], []]) == []
