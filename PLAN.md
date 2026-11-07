# Plan

Every stub raises `NotImplementedError`, and `uv run pytest` reports its spec tests as xfailed. When you implement a stub, its tests start counting, so watch xfails turn into passes. Commit every day, with real dates.

## Week 1: retrieval

- [ ] `chunking.split_markdown`. Tests in `tests/test_chunking.py`.
- [ ] `make db corpus ingest`. Note the chunk count here.
- [ ] `retrieval.vector_search`, `keyword_search`, `rrf_merge`, `hybrid_search`. Spec in `tests/test_retrieval.py`.
- [ ] `evals.metrics.first_hit_rank`, `recall_at_k`, `mrr`. Spec in `tests/test_metrics.py`.
- [ ] Write `GUIDELINES.md` before labelling anything.
- [ ] Grow `data/golden.jsonl` to 150 items, about 30 of them unanswerable. `pytest` checks every quote against the corpus.
- [ ] Ablation: recall@5 and MRR for dense only, keyword only, and hybrid.

## Week 2: answers and the judge

- [ ] `answer.answer`, including the tool-call loop.
- [ ] `tools.authorize`. Spec in `tests/test_tools.py`.
- [ ] `evals.judge.judge`, with the same rubric as `GUIDELINES.md`.
- [ ] `evals.metrics.cohens_kappa`. Hand-label 50 judged rows into `data/human_labels.jsonl`, then run `python -m owasp_rag.evals agreement results/<run>.jsonl`.
- [ ] Baseline `make eval-golden`: answer accuracy, refusal accuracy, p95 latency, cost per 1k queries.

## Week 3: attacks and defenses

- [ ] `evals.metrics.attack_succeeded`.
- [ ] Grow `data/attacks.jsonl` past 100 cases across all four categories.
- [ ] Baseline `make eval-attacks`.
- [ ] `defenses.spotlight`, `defenses.injection_score`, and the `tool_confirmation` path.
- [ ] Run each defense alone and all together. For each run, record attack success rate and answer accuracy.

## Week 4: ship

- [ ] Rate limit and a hard spend cap on `/ask` before it goes public.
- [ ] Dockerfile, then deploy to Cloud Run or Hugging Face Spaces.
- [ ] CI job that runs a smoke subset (`--limit 30`) against thresholds.
- [ ] Rewrite `README.md` in your own words, with the results table and a Limitations section.
- [ ] Record a 2-minute demo video. Write one blog post.

## Decisions log

Record each choice, the alternative you rejected, and the number that decided it.

| Date | Decision | Why |
|---|---|---|
| | | |

## Results

| Run | Defenses | recall@5 | MRR | Answer acc. | Refusal acc. | Attack success | p95 latency | $/1k queries |
|---|---|---|---|---|---|---|---|---|
| | none | | | | | | | |
