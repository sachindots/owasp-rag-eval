from collections import Counter

from owasp_rag.retrieval import Bm25, rrf_merge
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


def test_bm25_rare_term_outranks_common_term():
    docs = {
        "common": Counter({"password": 3}),
        "rare": Counter({"argon2id": 1}),
        **{f"filler{i}": Counter({"password": 1}) for i in range(5)},
    }
    assert Bm25(docs).top(["password", "argon2id"], 1) == ["rare"]


def test_bm25_prefers_shorter_document_at_equal_term_count():
    docs = {"long": Counter({"csrf": 1, "x": 40}), "short": Counter({"csrf": 1, "y": 2})}
    assert Bm25(docs).top(["csrf"], 2) == ["short", "long"]


def test_bm25_unknown_terms_return_nothing():
    assert Bm25({"a": Counter({"x": 1})}).top(["nope"], 5) == []
