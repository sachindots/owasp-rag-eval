import argparse
import json
import random
import statistics
import time
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from ..answer import answer
from ..config import settings
from ..db import connect
from ..llm import embed
from ..retrieval import hybrid_search, keyword_search, vector_search
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
from .grounding import citation_validity
from .judge import is_refusal, judge
from .metrics import (
    attack_succeeded,
    ci95,
    cohens_kappa,
    first_hit_rank,
    mrr,
    recall_at_k,
)

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


def results_file(kind: str) -> Path:
    RESULTS.mkdir(exist_ok=True)
    return RESULTS / f"{kind}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"


def append(path: Path, row: BaseModel) -> None:
    """One row per line as soon as it exists, so a crash keeps the rows already paid for."""
    with path.open("a", encoding="utf-8") as out:
        out.write(row.model_dump_json() + "\n")


def run_golden(split: str, limit: int | None, defenses: Defenses) -> dict:
    items = [i for i in load(DATA / "golden.jsonl", GoldenItem) if i.split == split][:limit]
    path = results_file("golden")
    rows: list[GoldenResult] = []
    with connect() as conn:
        for item in items:
            ans = answer(item.question, conn=conn, defenses=defenses)
            refused = ans.refused
            if not item.answerable:
                refused = refused or is_refusal(item.question, ans.text)
                rank, verdict, correct = None, None, refused
            elif refused:
                rank, verdict, correct = first_hit_rank(item.evidence, ans.retrieved), None, False
            else:
                rank = first_hit_rank(item.evidence, ans.retrieved)
                verdict = judge(item.question, item.reference_answer or "", ans.text)
                correct = verdict.correct
                # Only an answer judged wrong can be a free-worded refusal.
                refused = not correct and is_refusal(item.question, ans.text)
            rows.append(
                GoldenResult(
                    item_id=item.id,
                    answerable=item.answerable,
                    answer=ans,
                    hit_rank=rank,
                    judge=verdict,
                    correct=correct,
                    refused=refused,
                    citation_validity=None if refused else citation_validity(ans),
                )
            )
            append(path, rows[-1])
    answerable = [r for r in rows if r.answerable]
    unanswerable = [r for r in rows if not r.answerable]
    ranks = [r.hit_rank for r in answerable]
    return {
        "results": str(path),
        "split": split,
        "model": settings.llm_model,
        "judge_model": settings.judge_model,
        "defenses": defenses.model_dump(),
        "n": len(rows),
        f"recall_at_{settings.top_k}": recall_at_k(ranks, settings.top_k) if ranks else None,
        "mrr": mrr(ranks) if ranks else None,
        "answer_accuracy": mean([r.correct for r in answerable]),
        "answer_accuracy_ci95": ci95([r.correct for r in answerable]),
        "refusal_accuracy": mean([r.correct for r in unanswerable]),
        "refusal_accuracy_ci95": ci95([r.correct for r in unanswerable]),
        "false_refusal_rate": mean([bool(r.refused) for r in answerable]),
        "citation_validity": mean(
            [r.citation_validity for r in rows if r.citation_validity is not None]
        ),
        **ops([r.answer for r in rows]),
    }


def run_attacks(split: str, limit: int | None, defenses: Defenses) -> dict:
    items = [i for i in load(DATA / "attacks.jsonl", AttackItem) if i.split == split][:limit]
    path = results_file("attacks")
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
            append(path, rows[-1])
    by_category: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        by_category[r.category].append(r.succeeded)
    return {
        "results": str(path),
        "split": split,
        "model": settings.llm_model,
        "defenses": defenses.model_dump(),
        "n": len(rows),
        "attack_success_rate": mean([r.succeeded for r in rows]),
        "by_category": {c: mean(flags) for c, flags in sorted(by_category.items())},
        **ops([r.answer for r in rows]),
    }


def run_retrieval(split: str, limit: int | None) -> dict:
    """recall@k and MRR for dense only, keyword only and hybrid search. No LLM calls."""
    items = [
        i for i in load(DATA / "golden.jsonl", GoldenItem) if i.split == split and i.answerable
    ][:limit]
    k = settings.top_k
    ranks: dict[str, list[int | None]] = defaultdict(list)
    keyword_empty = 0
    with connect() as conn:
        for item in items:
            keyword = keyword_search(conn, item.question, k)
            keyword_empty += not keyword
            searches = {
                "dense": vector_search(conn, embed([item.question])[0], k),
                "keyword": keyword,
                "hybrid": hybrid_search(conn, item.question, k),
            }
            for mode, chunks in searches.items():
                ranks[mode].append(first_hit_rank(item.evidence, chunks))
    summary = {
        "split": split,
        "n": len(items),
        "k": k,
        "keyword_empty_rate": keyword_empty / len(items) if items else None,
        **{mode: {f"recall_at_{k}": recall_at_k(r, k), "mrr": mrr(r)} for mode, r in ranks.items()},
    }
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"retrieval-{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return {"results": str(path), **summary}


def run_label(results: Path, n: int) -> dict:
    """Blind-label judged rows: the judge's verdict is hidden so it can't anchor yours."""
    labels_path = DATA / "human_labels.jsonl"
    done = {
        lab.item_id
        for lab in (load(labels_path, HumanLabel) if labels_path.exists() else [])
        if lab.run == results.stem
    }
    items = {i.id: i for i in load(DATA / "golden.jsonl", GoldenItem)}
    rows = [r for r in load(results, GoldenResult) if r.judge is not None]
    random.Random(results.stem).shuffle(rows)
    todo = [r for r in rows if r.item_id not in done][: max(n - len(done), 0)]
    print(f"{len(done)} labelled for {results.stem}; {len(todo)} to go. Rubric: GUIDELINES.md")
    added = 0
    with labels_path.open("a", encoding="utf-8") as out:
        for r in todo:
            item = items[r.item_id]
            print(f"\n[{r.item_id}] {item.question}\n\nREFERENCE\n{item.reference_answer}")
            print(f"\nCANDIDATE\n{r.answer.text}\n")
            choice = ""
            while choice not in ("c", "i", "s", "q"):
                choice = input("correct, incorrect, skip, quit [c/i/s/q]: ").strip().lower()
            if choice == "q":
                break
            if choice == "s":
                continue
            label = HumanLabel(run=results.stem, item_id=r.item_id, correct=choice == "c")
            out.write(label.model_dump_json() + "\n")
            out.flush()
            added += 1
    return {"run": results.stem, "added": added, "total": len(done) + added}


def run_grounding(results: Path) -> dict:
    """MiniCheck support for every sentence of every answered row of a golden results file.
    A separate step so evals stay fast and runs made earlier can be scored too."""
    from .grounding import MODEL, sentence_support

    rows = [r for r in load(results, GoldenResult) if not r.refused and not r.answer.refused]
    support = {r.item_id: sentence_support(r.answer) for r in rows}
    supported = [p > 0.5 for scores in support.values() for p in scores]
    summary = {
        "run": results.stem,
        "model": MODEL,
        "answers": len(rows),
        "sentences": len(supported),
        # Share of answer sentences supported by the passages they cite.
        "groundedness": mean(supported),
        "groundedness_ci95": ci95(supported),
        "fully_grounded_answers": mean([all(p > 0.5 for p in s) for s in support.values() if s]),
        "support": support,
    }
    path = results.with_name(f"{results.stem}.grounding.json")
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return {"results": str(path), **{k: v for k, v in summary.items() if k != "support"}}


def run_agreement(results: Path) -> dict:
    labels_path = DATA / "human_labels.jsonl"
    if not labels_path.exists():
        raise SystemExit(f"{labels_path} not found; label some judged rows first")
    labels = {
        lab.item_id: lab.correct for lab in load(labels_path, HumanLabel) if lab.run == results.stem
    }
    judged = [r for r in load(results, GoldenResult) if r.judge and r.item_id in labels]
    pairs = [(r.judge.correct, labels[r.item_id]) for r in judged]
    ids = [r.item_id for r in judged]
    if not pairs:
        raise SystemExit(f"no human labels for judged rows of run {results.stem}")
    judge_labels, human_labels = zip(*pairs, strict=True)
    agree = [j == h for j, h in pairs]
    return {
        "run": results.stem,
        "n": len(pairs),
        "kappa": cohens_kappa(judge_labels, human_labels),
        "percent_agreement": mean(agree),
        "percent_agreement_ci95": ci95(agree),
        # A judge that says "correct" more often than the human is lenient.
        "judge_correct_rate": mean(judge_labels),
        "human_correct_rate": mean(human_labels),
        "disagreements": [r for (j, h), r in zip(pairs, ids, strict=True) if j != h],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m owasp_rag.evals")
    sub = parser.add_subparsers(dest="suite", required=True)
    for name in ("golden", "attacks"):
        p = sub.add_parser(name)
        p.add_argument("--split", choices=("dev", "test"), default="test")
        p.add_argument("--limit", type=int, help="run only the first N items (smoke runs)")
        p.add_argument(
            "--defenses",
            type=parse_defenses,
            default=NO_DEFENSES,
            help="comma-separated: spotlight,classifier,tool_confirmation",
        )
    ret = sub.add_parser("retrieval", help="retrieval-only ablation: dense, keyword, hybrid")
    ret.add_argument("--split", choices=("dev", "test"), default="test")
    ret.add_argument("--limit", type=int)
    gr = sub.add_parser("grounding", help="MiniCheck groundedness of a golden results file")
    gr.add_argument("results", type=Path, help="a results/golden-*.jsonl file")
    lab = sub.add_parser("label", help="blind-label judged rows for the agreement check")
    lab.add_argument("results", type=Path, help="a results/golden-*.jsonl file")
    lab.add_argument("--n", type=int, default=50, help="stop once this many rows are labelled")
    agree = sub.add_parser("agreement", help="Cohen's kappa between the judge and your labels")
    agree.add_argument("results", type=Path, help="a results/golden-*.jsonl file")
    args = parser.parse_args(argv)

    if args.suite == "golden":
        summary = run_golden(args.split, args.limit, args.defenses)
    elif args.suite == "attacks":
        summary = run_attacks(args.split, args.limit, args.defenses)
    elif args.suite == "grounding":
        summary = run_grounding(args.results)
    elif args.suite == "label":
        summary = run_label(args.results, args.n)
    elif args.suite == "retrieval":
        summary = run_retrieval(args.split, args.limit)
    else:
        summary = run_agreement(args.results)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
