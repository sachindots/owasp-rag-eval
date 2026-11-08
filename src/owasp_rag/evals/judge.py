import time
from functools import cache
from pathlib import Path

from openai import RateLimitError
from pydantic import ValidationError

from ..config import settings
from ..llm import judge_client
from ..schemas import JudgeVerdict

GUIDELINES = Path(__file__).resolve().parents[3] / "GUIDELINES.md"
RUBRIC_HEADING = "## Correctness rubric (binary)"

SYSTEM = """You grade answers from a security assistant against a reference answer written by a \
human annotator. Apply this rubric exactly.

{rubric}

Judge only whether the candidate's content is correct under the rubric. Ignore citation markers \
such as [Some_Cheat_Sheet#3], style and length.

Reply with only a JSON object, rationale first, in one or two sentences, then the verdict:
{{"rationale": "...", "correct": true or false}}"""

USER = """Question:
{question}

Reference answer:
{reference}

Candidate answer:
{candidate}"""

_last_call = 0.0


def _create(**kwargs):
    """Call the judge, spaced to settings.judge_rpm and waiting out 429s, so a free-tier
    quota slows a run down instead of killing it."""
    global _last_call
    for wait in (60, 120, 240, None):
        time.sleep(max(0.0, _last_call + 60 / settings.judge_rpm - time.monotonic()))
        _last_call = time.monotonic()
        try:
            return judge_client().chat.completions.create(**kwargs)
        except RateLimitError:
            if wait is None:
                raise
            time.sleep(wait)


@cache
def rubric() -> str:
    """The correctness rubric section of GUIDELINES.md, word for word."""
    text = GUIDELINES.read_text(encoding="utf-8")
    start = text.index(RUBRIC_HEADING) + len(RUBRIC_HEADING)
    end = text.find("\n## ", start)
    return text[start : end if end != -1 else None].strip()


def judge(question: str, reference_answer: str, candidate: str) -> JudgeVerdict:
    """Grade the candidate answer against the reference with settings.judge_model.

    Write the correctness rubric in GUIDELINES.md first and put the same rubric in the judge
    prompt, so a human label and a judge label mean the same thing. Ask for JSON matching
    JudgeVerdict and validate it with JudgeVerdict.model_validate_json.
    """
    messages = [
        {"role": "system", "content": SYSTEM.format(rubric=rubric())},
        {
            "role": "user",
            "content": USER.format(
                question=question, reference=reference_answer, candidate=candidate
            ),
        },
    ]
    error: ValidationError | None = None
    for _ in range(3):
        resp = _create(
            model=settings.judge_model,
            messages=messages,
            temperature=0,
            # JSON mode, not a strict schema: gpt-oss on Ollama Cloud ignores json_schema.
            response_format={"type": "json_object"},
        )
        try:
            return JudgeVerdict.model_validate_json(resp.choices[0].message.content or "")
        except ValidationError as e:
            error = e
    raise RuntimeError(f"judge returned invalid JSON three times: {error}")


REFUSAL_SYSTEM = """You classify replies from a security assistant that answers only from the \
OWASP Cheat Sheets. A reply is a refusal when it declines to answer the question or says the \
available material does not contain the answer, even if it then mentions related material. \
A reply that answers the question, fully or partly, is not a refusal.

Reply with only a JSON object: {"rationale": "...", "correct": true if the reply is a refusal, \
false otherwise}"""


def is_refusal(question: str, reply: str) -> bool:
    """Whether a reply declines to answer, in any wording. Uses the judge model."""
    messages = [
        {"role": "system", "content": REFUSAL_SYSTEM},
        {"role": "user", "content": f"Question:\n{question}\n\nReply:\n{reply}"},
    ]
    for _ in range(3):
        resp = _create(
            model=settings.judge_model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        try:
            return JudgeVerdict.model_validate_json(resp.choices[0].message.content or "").correct
        except ValidationError:
            continue
    raise RuntimeError("refusal check returned invalid JSON three times")
