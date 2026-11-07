from typing import Any

from .schemas import Defenses, ToolStatus

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Open a security ticket for the user's team.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                },
                "required": ["title", "severity"],
            },
        },
    }
]

SIDE_EFFECT_TOOLS = frozenset({"create_ticket"})

# shortcut: in-memory mock tracker, swap for a real issue tracker call if you ever need one.
TICKETS: list[dict[str, Any]] = []


def run_tool(name: str, arguments: dict[str, Any]) -> str:
    if name != "create_ticket":
        raise ValueError(f"unknown tool {name!r}")
    TICKETS.append(arguments)
    return f"ticket #{len(TICKETS)} created"


def authorize(name: str, arguments: dict[str, Any], defenses: Defenses) -> ToolStatus:
    """Decide what happens to a tool call the model asked for, before anything runs.

    - A name not in TOOL_SPECS is "blocked".
    - A side-effect tool with defenses.tool_confirmation on is "pending_confirmation".
    - Anything else is "executed".
    """
    raise NotImplementedError
