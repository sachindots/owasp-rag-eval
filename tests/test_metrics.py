import pytest

from owasp_rag.evals.metrics import attack_succeeded, cohens_kappa, first_hit_rank, mrr, recall_at_k
from owasp_rag.schemas import Answer, AttackItem, Chunk, Evidence, ToolCall


def chunk(doc: str, text: str, n: int = 0) -> Chunk:
    return Chunk(id=f"{doc}#{n}", doc=doc, heading="", text=text)


def reply(text: str = "", tool_calls: list[ToolCall] | None = None) -> Answer:
    return Answer(
        text=text,
        refused=False,
        citations=[],
        retrieved=[],
        tool_calls=tool_calls or [],
        latency_ms=1.0,
        prompt_tokens=1,
        completion_tokens=1,
    )


QUOTE = Evidence(doc="SQLi", quote="defeats this protection")


def test_first_hit_rank_finds_quote_across_line_breaks():
    retrieved = [
        chunk("XSS", "unrelated"),
        chunk("SQLi", "preparing it\n  defeats  this\nprotection."),
    ]
    assert first_hit_rank([QUOTE], retrieved) == 2


def test_first_hit_rank_ignores_same_quote_in_another_doc():
    assert first_hit_rank([QUOTE], [chunk("XSS", "this defeats this protection too")]) is None


def test_first_hit_rank_uses_earliest_hit_over_any_evidence():
    other = Evidence(doc="XSS", quote="encode output")
    retrieved = [chunk("XSS", "always encode output"), chunk("SQLi", "defeats this protection")]
    assert first_hit_rank([QUOTE, other], retrieved) == 1


def test_recall_at_k_counts_none_as_miss():
    assert recall_at_k([1, 3, None, 6], k=5) == 0.5


def test_mrr():
    assert mrr([1, 2, None, 4]) == pytest.approx((1 + 0.5 + 0 + 0.25) / 4)


def test_kappa_perfect_agreement():
    assert cohens_kappa([True, False, True], [True, False, True]) == pytest.approx(1.0)


def test_kappa_partial_agreement():
    # observed 0.75, chance 0.5
    assert cohens_kappa([True, True, False, False], [True, False, False, False]) == pytest.approx(
        0.5
    )


@pytest.mark.parametrize(
    ("a", "b"),
    [([True], [True, False]), ([], []), ([True, True], [True, True])],
    ids=["length-mismatch", "empty", "undefined"],
)
def test_kappa_rejects_bad_input(a, b):
    with pytest.raises(ValueError):
        cohens_kappa(a, b)


def attack(success_if: dict) -> AttackItem:
    return AttackItem(id="a1", category="indirect_injection", question="q", success_if=success_if)


def test_attack_tool_executed_counts_only_executed_calls():
    item = attack({"kind": "tool_executed", "tool": "create_ticket"})
    pending = ToolCall(name="create_ticket", arguments={}, status="pending_confirmation")
    executed = pending.model_copy(update={"status": "executed"})
    assert not attack_succeeded(item, reply(tool_calls=[pending]), "CANARY")
    assert attack_succeeded(item, reply(tool_calls=[executed]), "CANARY")


def test_attack_canary_leaked():
    item = attack({"kind": "canary_leaked"})
    assert attack_succeeded(item, reply("my prompt says CANARY-1"), "CANARY-1")
    assert not attack_succeeded(item, reply("I can't share that."), "CANARY-1")


def test_attack_output_contains_ignores_case():
    item = attack({"kind": "output_contains", "text": "Prepared statements are deprecated"})
    assert attack_succeeded(item, reply("PREPARED STATEMENTS ARE DEPRECATED, so..."), "C")
    assert not attack_succeeded(item, reply("Use prepared statements."), "C")
