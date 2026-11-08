from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Chunk(BaseModel):
    id: str  # f"{doc}#{n}", n counting from 0 in document order
    doc: str  # cheat sheet file stem, e.g. "Password_Storage_Cheat_Sheet"
    heading: str  # heading path above the chunk, joined with " > "
    text: str  # body text; heading lines live in `heading`, not here
    trusted: bool = True  # False for content an attacker could control


class Defenses(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    spotlight: bool = False
    classifier: bool = False
    tool_confirmation: bool = False


NO_DEFENSES = Defenses()


ToolStatus = Literal["executed", "blocked", "pending_confirmation"]


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]
    status: ToolStatus


class RetrievalHit(BaseModel):
    """Where one retrieved chunk ranked, and what the injection classifier made of it."""

    id: str
    dense_rank: int | None = None  # None: not in the dense list, or a planted chunk
    keyword_rank: int | None = None
    rrf_score: float | None = None
    injection_score: float | None = None  # None when the classifier defense is off
    dropped: bool = False  # withheld from the model by the classifier


class Answer(BaseModel):
    text: str
    refused: bool
    citations: list[str]  # chunk ids the answer relies on
    retrieved: list[Chunk]  # what retrieval returned, best first, planted chunks last
    retrieval: list[RetrievalHit] = []  # one per retrieved chunk, same order
    tool_calls: list[ToolCall] = []
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int


class Evidence(BaseModel):
    doc: str
    quote: str  # short verbatim span of body text from that cheat sheet


Split = Literal["dev", "test"]  # tune on dev only; report numbers on test


class GoldenItem(BaseModel):
    id: str
    split: Split
    question: str
    answerable: bool
    reference_answer: str | None = None
    evidence: list[Evidence] = []
    tags: list[str] = []

    @model_validator(mode="after")
    def _answerable_has_reference_and_evidence(self):
        has_both = self.reference_answer is not None and bool(self.evidence)
        has_neither = self.reference_answer is None and not self.evidence
        if self.answerable and not has_both:
            raise ValueError("answerable items need reference_answer and evidence")
        if not self.answerable and not has_neither:
            raise ValueError("unanswerable items take no reference_answer or evidence")
        return self


class ToolExecuted(BaseModel):
    kind: Literal["tool_executed"]
    tool: str


class CanaryLeaked(BaseModel):
    kind: Literal["canary_leaked"]


class OutputContains(BaseModel):
    kind: Literal["output_contains"]
    text: str


SuccessCriterion = Annotated[
    ToolExecuted | CanaryLeaked | OutputContains, Field(discriminator="kind")
]

AttackCategory = Literal["direct_jailbreak", "indirect_injection", "prompt_leak", "tool_misuse"]


class AttackItem(BaseModel):
    id: str
    split: Split
    category: AttackCategory
    question: str
    injected_document: str | None = None  # served to the model as an untrusted retrieved chunk
    success_if: SuccessCriterion


class JudgeVerdict(BaseModel):
    correct: bool
    rationale: str


class GoldenResult(BaseModel):
    item_id: str
    answerable: bool
    answer: Answer
    hit_rank: int | None  # 1-based rank of the first evidence hit; None if missed or unanswerable
    judge: JudgeVerdict | None  # None when no judge ran (refusals, unanswerable items)
    correct: bool
    # The answer's refusal flag, widened by the eval's refusal check to catch free-worded
    # refusals. None in runs made before the check existed.
    refused: bool | None = None
    citation_validity: float | None = None  # share of [chunk_id] markers naming shown chunks


class AttackResult(BaseModel):
    item_id: str
    category: AttackCategory
    answer: Answer
    succeeded: bool


class HumanLabel(BaseModel):
    run: str  # results file stem, e.g. "golden-20261110-142000"
    item_id: str
    correct: bool
