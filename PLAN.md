# Plan

Every stub raises `NotImplementedError`, and `uv run pytest` reports its spec tests as xfailed. When you implement a stub, its tests start counting, so watch xfails turn into passes. Commit every day, with real dates.

## Week 1: retrieval

- [x] `chunking.split_markdown`. Tests in `tests/test_chunking.py`.
- [x] `make db corpus ingest`. 3,298 chunks from 137 cheat sheets at corpus commit `757270a`, 1024-dim bge-m3 embeddings, about 2 minutes on an RTX 3060 Laptop GPU.
- [ ] `retrieval.vector_search`, `keyword_search`, `rrf_merge`, `hybrid_search`. Spec in `tests/test_retrieval.py`.
- [x] `evals.metrics.first_hit_rank`, `recall_at_k`, `mrr`. Spec in `tests/test_metrics.py`.
- [x] Write `GUIDELINES.md` before labelling anything.
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
| 2026-11-07 | Pin the corpus to commit `757270a` instead of cloning the latest | The upstream text changes: the Argon2id section was rewritten into a parameter list. A moving corpus breaks evidence quotes without warning. |
| 2026-11-07 | Chunker uses CommonMark fence rules, any indentation, and keeps oversized single blocks whole | One line of inline code with ``` at both ends (`Authorization_Cheat_Sheet.md`) swallowed 77 headings under a naive fence regex. 19 fences sit indented in lists. 46 of 3,298 chunks exceed 2,000 chars (tables, long lists, code); bge-m3 accepts 8,192 tokens, so splitting them further buys little. |
| 2026-11-07 | Answer model `qwen3.5:4b`, not `qwen3:8b` | qwen3:8b (5.2 GB) plus bge-m3 (1.2 GB) does not fit in 6 GB of VRAM; qwen3.5:4b at 16K context uses 3.4 GB. |
| 2026-11-07 | Judge on Gemini, a different model family from the answer model | Same-family judges favour their own outputs. |
| 2026-11-07 | Golden and attack items carry a `dev`/`test` split | Prompts and thresholds are tuned on `dev`; reported numbers come from `test` only. |

## Results

| Run | Defenses | recall@5 | MRR | Answer acc. | Refusal acc. | Attack success | p95 latency | $/1k queries |
|---|---|---|---|---|---|---|---|---|
| | none | | | | | | | |
