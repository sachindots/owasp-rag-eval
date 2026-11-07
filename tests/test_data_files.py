import re
from collections import Counter
from pathlib import Path

import pytest
from pydantic import BaseModel

from owasp_rag.chunking import split_markdown
from owasp_rag.schemas import AttackItem, GoldenItem

DATA = Path(__file__).parent.parent / "data"


@pytest.mark.parametrize(("name", "model"), [("golden", GoldenItem), ("attacks", AttackItem)])
def test_data_file_parses_with_unique_ids(name: str, model: type[BaseModel]):
    lines = [x for x in (DATA / f"{name}.jsonl").read_text(encoding="utf-8").splitlines() if x]
    items = [model.model_validate_json(line) for line in lines]
    assert items, f"{name}.jsonl is empty"
    ids = [i.id for i in items]
    assert len(ids) == len(set(ids)), "duplicate ids"


CORPUS = DATA / "corpus" / "cheatsheets"


@pytest.mark.skipif(not CORPUS.exists(), reason="run `make corpus` to check quotes")
def test_every_evidence_quote_is_verbatim_in_its_cheat_sheet():
    def norm(s: str) -> str:
        return " ".join(s.split())

    lines = (DATA / "golden.jsonl").read_text(encoding="utf-8").splitlines()
    missing = [
        (item.id, ev.doc)
        for item in (GoldenItem.model_validate_json(x) for x in lines if x)
        for ev in item.evidence
        if not (CORPUS / f"{ev.doc}.md").exists()
        or norm(ev.quote) not in norm((CORPUS / f"{ev.doc}.md").read_text(encoding="utf-8"))
    ]
    assert not missing, f"quotes not found verbatim: {missing}"


def test_golden_rejects_answerable_item_without_evidence():
    with pytest.raises(ValueError):
        GoldenItem(id="x", split="dev", question="q", answerable=True, reference_answer="r")


# The rules below encode GUIDELINES.md, so a bad item fails here instead of skewing a metric.

STOP = set(
    "a an the of to in on for and or is are be it its this that with as by at from into your you"
    " i my me do does should can how what why when which use".split()
)


def golden_items() -> list[GoldenItem]:
    lines = (DATA / "golden.jsonl").read_text(encoding="utf-8").splitlines()
    return [GoldenItem.model_validate_json(x) for x in lines if x]


def content_ngrams(text: str, n: int = 4) -> set[tuple[str, ...]]:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def test_quotes_are_short_plain_body_text():
    bad = [
        (item.id, ev.quote)
        for item in golden_items()
        for ev in item.evidence
        if not 5 <= len(ev.quote.split()) <= 25 or any(m in ev.quote for m in ("**", "`", "]("))
    ]
    assert not bad, bad


def test_questions_do_not_copy_their_evidence():
    copied = [
        item.id
        for item in golden_items()
        for ev in item.evidence
        if content_ngrams(item.question) & content_ngrams(ev.quote)
    ]
    assert not copied, f"questions share 4+ content words with their quote: {copied}"


def test_no_cheat_sheet_supplies_more_than_six_items():
    counts = Counter(doc for item in golden_items() for doc in {ev.doc for ev in item.evidence})
    assert not [d for d, n in counts.items() if n > 6], counts.most_common(5)


def test_dev_split_is_about_thirty_percent():
    items = golden_items()
    if len(items) < 50:
        pytest.skip("split share is checked once the set is built")
    assert 0.2 <= sum(i.split == "dev" for i in items) / len(items) <= 0.4


@pytest.mark.skipif(not CORPUS.exists(), reason="run `make corpus` to check quotes")
def test_every_quote_lies_inside_a_single_chunk():
    def norm(s: str) -> str:
        return " ".join(s.split())

    chunks: dict[str, list[str]] = {}
    for item in golden_items():
        for ev in item.evidence:
            if ev.doc not in chunks:
                md = (CORPUS / f"{ev.doc}.md").read_text(encoding="utf-8")
                chunks[ev.doc] = [norm(c.text) for c in split_markdown(ev.doc, md)]
    split_quotes = [
        (item.id, ev.quote)
        for item in golden_items()
        for ev in item.evidence
        if not any(norm(ev.quote) in text for text in chunks[ev.doc])
    ]
    assert not split_quotes, split_quotes
