import argparse
import json
import statistics
import time
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from ..answer import answer
from ..config import settings
from ..db import connect
from ..schemas import (
    NO_DEFENSES,
    Answer,
    AttackItem,
    AttackResult,
    Chunk,
    Defenses,
    GoldenItem,
    GoldenResult,
    HumanLabel,
)
from .judge import judge
from .metrics import attack_succeeded, cohens_kappa, first_hit_rank, mrr, recall_at_k

DATA = Path("data")
RESULTS = Path("results")


def load[M: BaseModel](path: Path, model: type[M]) -> list[M]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [model.model_validate_json(line) for line in lines if line.strip()]


def parse_defenses(value: str) -> Defenses:
    return Defenses(**{name: True for name in value.split(",") if name})


def mean(flags: Sequence[bool]) -> float | None:
    return sum(flags) / len(flags) if flags else None


def ops(answers: Sequence[Answer]) -> dict[str, float]:
    if not answers:
        return {}
    latencies = [a.latency_ms for a in answers]
    if len(latencies) == 1:
        p50 = p95 = latencies[0]
    else:
        pct = statistics.quantiles(latencies, n=100)
        p50, p95 = pct[49], pct[94]
    tokens_in = sum(a.prompt_tokens for a in answers)
    tokens_out = sum(a.completion_tokens for a in answers)
    cost = (tokens_in * settings.price_in_per_mtok + tokens_out * settings.price_out_per_mtok) / 1e6
    return {
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "cost_per_1k_queries_usd": cost / len(answers) * 1000,
    }


def write(kind: str, rows: Sequence[BaseModel]) -> Path:
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"{kind}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    path.write_text("".join(r.model_dump_json() + "\n" for r in rows), encoding="utf-8")
    return path


def run_golden(limit: int | None, defenses: Defenses) -> dict:
    items = load(DATA / "golden.jsonl", GoldenItem)[:limit]
    rows: list[GoldenResult] = []
    with connect() as conn:
        for item in items:
            ans = answer(item.question, conn=conn, defenses=defenses)
            if not item.answerable:
                rank, verdict, correct = None, None, ans.refused
            elif ans.refused:
                rank, verdict, correct = first_hit_rank(item.evidence, ans.retrieved), None, False
            else:
                rank = first_hit_rank(item.evidence, ans.retrieved)
                verdict = judge(item.question, item.reference_answer or "", ans.text)
                correct = verdict.correct
            rows.append(
                GoldenResult(
                    item_id=item.id,
                    answerable=item.answerable,
                    answer=ans,
                    hit_rank=rank,
                    judge=verdict,
                    correct=correct,
                )
            )
    answerable = [r for r in rows if r.answerable]
    ranks = [r.hit_rank for r in answerable]
    return {
        "results": str(write("golden", rows)),
        "defenses": defenses.model_dump(),
        "n": len(rows),
        f"recall_at_{settings.top_k}": recall_at_k(ranks, settings.top_k) if ranks else None,
        "mrr": mrr(ranks) if ranks else None,
        "answer_accuracy": mean([r.correct for r in answerable]),
        "refusal_accuracy": mean([r.correct for r in rows if not r.answerable]),
        **ops([r.answer for r in rows]),
    }


def run_attacks(limit: int | None, defenses: Defenses) -> dict:
    items = load(DATA / "attacks.jsonl", AttackItem)[:limit]
    rows: list[AttackResult] = []
    with connect() as conn:
        for item in items:
            planted = (
                [
                    Chunk(
                        id=f"injected#{item.id}",
                        doc="injected",
                        heading="",
                        text=item.injected_document,
                        trusted=False,
                    )
                ]
                if item.injected_document
                else []
            )
            ans = answer(item.question, conn=conn, defenses=defenses, extra_chunks=planted)
            rows.append(
                AttackResult(
                    item_id=item.id,
                    category=item.category,
                    answer=ans,
                    succeeded=attack_succeeded(item, ans, settings.canary),
                )
            )
    by_category: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        by_category[r.category].append(r.succeeded)
    return {
        "results": str(write("attacks", rows)),
        "defenses": defenses.model_dump(),
        "n": len(rows),
        "attack_success_rate": mean([r.succeeded for r in rows]),
        "by_category": {c: mean(flags) for c, flags in sorted(by_category.items())},
        **ops([r.answer for r in rows]),
    }


def run_agreement(results: Path) -> dict:
    labels_path = DATA / "human_labels.jsonl"
    if not labels_path.exists():
        raise SystemExit(f"{labels_path} not found; label some judged rows first")
    labels = {
        lab.item_id: lab.correct for lab in load(labels_path, HumanLabel) if lab.run == results.stem
    }
    pairs = [
        (r.judge.correct, labels[r.item_id])
        for r in load(results, GoldenResult)
        if r.judge is not None and r.item_id in labels
    ]
    if not pairs:
        raise SystemExit(f"no human labels for judged rows of run {results.stem}")
    judge_labels, human_labels = zip(*pairs, strict=True)
    return {"run": results.stem, "n": len(pairs), "kappa": cohens_kappa(judge_labels, human_labels)}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m owasp_rag.evals")
    sub = parser.add_subparsers(dest="suite", required=True)
    for name in ("golden", "attacks"):
        p = sub.add_parser(name)
        p.add_argument("--limit", type=int, help="run only the first N items (smoke runs)")
        p.add_argument(
            "--defenses",
            type=parse_defenses,
            default=NO_DEFENSES,
            help="comma-separated: spotlight,classifier,tool_confirmation",
        )
    agree = sub.add_parser("agreement", help="Cohen's kappa between the judge and your labels")
    agree.add_argument("results", type=Path, help="a results/golden-*.jsonl file")
    args = parser.parse_args(argv)

    if args.suite == "golden":
        summary = run_golden(args.limit, args.defenses)
    elif args.suite == "attacks":
        summary = run_attacks(args.limit, args.defenses)
    else:
        summary = run_agreement(args.results)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
