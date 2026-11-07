from pathlib import Path

import pytest
from pydantic import BaseModel

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
        GoldenItem(id="x", question="q", answerable=True, reference_answer="r")
