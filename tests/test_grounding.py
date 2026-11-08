from owasp_rag.evals import grounding
from owasp_rag.schemas import Answer, Chunk, RetrievalHit


def answer(text: str, ids: list[str], dropped: frozenset[str] = frozenset()) -> Answer:
    return Answer(
        text=text,
        refused=False,
        citations=[],
        retrieved=[Chunk(id=i, doc="d", heading="", text=f"text of {i}") for i in ids],
        retrieval=[RetrievalHit(id=i, dropped=i in dropped) for i in ids],
        latency_ms=1,
        prompt_tokens=1,
        completion_tokens=1,
    )


def test_cited_sentences_split_and_strip_markers():
    text = "Use Argon2id [P#1]. Salt every hash [P#2] [P#1]! Done."
    assert grounding.cited_sentences(text) == [
        ("Use Argon2id.", ["P#1"]),
        ("Salt every hash!", ["P#2", "P#1"]),
        ("Done.", []),
    ]


def test_citation_validity_counts_markers_to_unshown_chunks():
    a = answer("A [P#1]. B [Made#9]. C [P#2].", ["P#1", "P#2"], dropped=frozenset({"P#2"}))
    assert grounding.citation_validity(a) == 1 / 3
    assert grounding.citation_validity(answer("No markers.", ["P#1"])) is None


def test_sentence_support_takes_best_cited_passage(monkeypatch):
    monkeypatch.setattr(
        grounding, "support_probability", lambda passage, claim: 0.9 if "P#2" in passage else 0.2
    )
    a = answer("One [P#1] [P#2]. Two [P#1]. Three.", ["P#1", "P#2"])
    assert grounding.sentence_support(a) == [0.9, 0.2, 0.0]
