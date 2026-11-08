"""Groundedness: is each answer sentence supported by the passages it cites?

Support is scored by MiniCheck-Flan-T5-Large (Tang et al., 2024, arXiv:2404.10774), following
its reference inference code (github.com/Liyan06/MiniCheck, minicheck/inference.py): the input is
"predict: " + passage + </s> + claim, one decoder step, and the support probability is the
softmax over token ids 3 (unsupported) and 209 (supported). Long passages are split into word
windows and the best window counts. Needs the optional `ml` dependency group.
"""

import re
from functools import cache

from ..schemas import Answer, Chunk

MODEL = "lytang/MiniCheck-Flan-T5-Large"
WINDOW_WORDS = 400  # keeps "predict: " + window + claim under the model's 2048-token input
_CITATION = re.compile(r"\[([^\[\]\s]+#\d+)\]")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def cited_sentences(text: str) -> list[tuple[str, list[str]]]:
    """(claim with citation markers removed, chunk ids it cites) for each sentence."""
    out = []
    for sentence in _SENTENCE_END.split(text.strip()):
        ids = list(dict.fromkeys(_CITATION.findall(sentence)))
        claim = re.sub(r"\s+([.,;:!?])", r"\1", " ".join(_CITATION.sub("", sentence).split()))
        if claim:
            out.append((claim, ids))
    return out


def citation_validity(answer: Answer) -> float | None:
    """Share of citation markers in the text that name a chunk the model was shown."""
    shown = {
        c.id for c, h in zip(answer.retrieved, answer.retrieval, strict=False) if not h.dropped
    }
    shown |= {c.id for c in answer.retrieved[len(answer.retrieval) :]}
    markers = _CITATION.findall(answer.text)
    return sum(m in shown for m in markers) / len(markers) if markers else None


def _windows(text: str) -> list[str]:
    words = text.split()
    return [" ".join(words[i : i + WINDOW_WORDS]) for i in range(0, len(words), WINDOW_WORDS)]


@cache
def _model():
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL).eval()
    return torch, tokenizer, model


def support_probability(passage: str, claim: str) -> float:
    """MiniCheck's probability that the passage supports the claim (max over windows)."""
    torch, tokenizer, model = _model()
    inputs = tokenizer(
        [f"predict: {w}{tokenizer.eos_token}{claim}" for w in _windows(passage) or [""]],
        max_length=2048,
        truncation=True,
        padding=True,
        return_tensors="pt",
    )
    with torch.no_grad():
        decoder_ids = torch.zeros((inputs["input_ids"].size(0), 1), dtype=torch.long)
        logits = model(**inputs, decoder_input_ids=decoder_ids).logits.squeeze(1)
    return torch.softmax(logits[:, [3, 209]], dim=-1)[:, 1].max().item()


def _with_source(chunk: Chunk) -> str:
    # Without its provenance a passage can't support "OWASP recommends ..." claims.
    source = f"OWASP {chunk.heading or chunk.doc}" if chunk.trusted else "an untrusted document"
    return f"Source: {source}\n\n{chunk.text}"


def sentence_support(answer: Answer) -> list[float]:
    """Support probability per answer sentence. A sentence is checked against the passages it
    cites, or against every passage the model was shown when it cites none (as RAGAS
    faithfulness does). Citation coverage is reported separately."""
    shown = {c.id for c, h in zip(answer.retrieved, answer.retrieval, strict=False) if h.dropped}
    shown = [c for c in answer.retrieved if c.id not in shown]
    by_id = {c.id: c for c in shown}
    scores = []
    for claim, ids in cited_sentences(answer.text):
        passages = [by_id[i] for i in ids if i in by_id] or shown
        scores.append(
            max((support_probability(_with_source(c), claim) for c in passages), default=0.0)
        )
    return scores
