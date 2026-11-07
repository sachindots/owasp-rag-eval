from collections.abc import Sequence

import psycopg

from .schemas import NO_DEFENSES, Answer, Chunk, Defenses


def answer(
    question: str,
    *,
    conn: psycopg.Connection,
    defenses: Defenses = NO_DEFENSES,
    extra_chunks: Sequence[Chunk] = (),
) -> Answer:
    """Answer from the cheat sheets with chunk-id citations, or refuse.

    The steps are yours to write:
    1. Retrieve with retrieval.hybrid_search(conn, question, settings.top_k), then append
       extra_chunks. The attack suite plants poisoned documents there, with trusted=False.
    2. With defenses.classifier on, drop chunks (and refuse questions) that
       defenses.injection_score flags above your threshold.
    3. Build the messages. The system prompt must contain settings.canary, so prompt-leak
       attacks are detectable, and must tell the model to cite chunk ids and to refuse when the
       context does not answer the question. Render chunks with defenses.spotlight when
       defenses.spotlight is on.
    4. Call llm.chat_client().chat.completions.create(..., tools=tools.TOOL_SPECS). For each
       tool call, take status from tools.authorize and call tools.run_tool only when it is
       "executed". Send tool results back and loop until the model answers in text, with a cap
       on the number of rounds.
    5. Fill citations and refused from the model output (structured output makes this easy),
       latency_ms from a wall clock, and token counts from each response's usage.
    """
    raise NotImplementedError
