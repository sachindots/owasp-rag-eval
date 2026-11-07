from types import SimpleNamespace as NS

import pytest

from owasp_rag.evals import judge as judge_mod


def test_rubric_is_read_from_guidelines():
    text = judge_mod.rubric()
    assert "Right but incomplete" in text
    assert "## Refusals" not in text


@pytest.fixture
def replies(monkeypatch):
    def install(*contents):
        sent = []

        def create(**kwargs):
            sent.append(kwargs)
            return NS(choices=[NS(message=NS(content=contents[len(sent) - 1]))])

        monkeypatch.setattr(
            judge_mod, "judge_client", lambda: NS(chat=NS(completions=NS(create=create)))
        )
        monkeypatch.setattr(judge_mod.settings, "judge_rpm", 1e9)
        return sent

    return install


def test_judge_sends_rubric_and_parses_verdict(replies):
    sent = replies('{"rationale": "matches", "correct": true}')
    verdict = judge_mod.judge("q", "ref", "cand")
    assert verdict.correct
    assert "Right but incomplete" in sent[0]["messages"][0]["content"]
    assert "cand" in sent[0]["messages"][1]["content"]
    assert sent[0]["temperature"] == 0


def test_judge_retries_invalid_json(replies):
    sent = replies("not json", '{"rationale": "wrong value", "correct": false}')
    assert judge_mod.judge("q", "ref", "cand").correct is False
    assert len(sent) == 2


def test_judge_gives_up_after_three_bad_replies(replies):
    replies("x", "y", "z")
    with pytest.raises(RuntimeError):
        judge_mod.judge("q", "ref", "cand")
