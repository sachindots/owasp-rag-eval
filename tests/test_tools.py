from owasp_rag.schemas import Defenses
from owasp_rag.tools import authorize

ARGS = {"title": "t", "severity": "low"}


def test_unknown_tool_is_blocked_even_without_defenses():
    assert authorize("delete_repo", ARGS, Defenses()) == "blocked"


def test_side_effect_tool_runs_without_confirmation_defense():
    assert authorize("create_ticket", ARGS, Defenses()) == "executed"


def test_side_effect_tool_waits_for_confirmation_when_defense_on():
    assert (
        authorize("create_ticket", ARGS, Defenses(tool_confirmation=True)) == "pending_confirmation"
    )
