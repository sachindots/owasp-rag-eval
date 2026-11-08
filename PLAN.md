# Plan

Every stub raises `NotImplementedError`, and `uv run pytest` reports its spec tests as xfailed. When you implement a stub, its tests start counting, so watch xfails turn into passes. Commit every day, with real dates.

## Week 1: retrieval

- [x] `chunking.split_markdown`. Tests in `tests/test_chunking.py`.
- [x] `make db corpus ingest`. 3,298 chunks from 137 cheat sheets at corpus commit `757270a`, 1024-dim bge-m3 embeddings, about 2 minutes on an RTX 3060 Laptop GPU.
- [x] `retrieval.vector_search`, `keyword_search`, `rrf_merge`, `hybrid_search`. Spec in `tests/test_retrieval.py`. Keyword search is in-memory BM25 over the lexemes in `chunks.tsv`.
- [x] `evals.metrics.first_hit_rank`, `recall_at_k`, `mrr`. Spec in `tests/test_metrics.py`.
- [x] Write `GUIDELINES.md` before labelling anything.
- [x] Grow `data/golden.jsonl` to 150 items, about 30 of them unanswerable. `pytest` checks every quote against the corpus. 154 items: 123 answerable, 31 unanswerable, 47 in `dev`. Frozen on 2026-11-07.
- [x] Ablation: recall@5 and MRR for dense only, keyword only, and hybrid. Test split, 85 answerable questions (`results/retrieval-20261107-231525.json`):

  | Retrieval | recall@5 | MRR |
  |---|---|---|
  | Dense (bge-m3) | 0.812 | 0.690 |
  | Keyword (BM25) | 0.847 | 0.691 |
  | Hybrid (RRF, k=60) | 0.906 | 0.733 |

## Week 2: answers and the judge

- [x] `answer.answer`, including the tool-call loop.
- [x] `tools.authorize`. Spec in `tests/test_tools.py`.
- [x] `evals.judge.judge`, with the same rubric as `GUIDELINES.md`. The rubric is read from `GUIDELINES.md` at run time.
- [ ] `evals.metrics.cohens_kappa`. Hand-label 50 judged rows into `data/human_labels.jsonl`, then run `python -m owasp_rag.evals agreement results/<run>.jsonl`.
- [x] Baseline `make eval-golden`: answer accuracy, refusal accuracy, p95 latency, cost per 1k queries. Test split, n=107, answer model `qwen3.5-4b-8k`, judge `gpt-oss:120b` (`results/golden-20261108-001902.summary.json`).

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
| 2026-11-07 | Answer model `qwen3.5:4b`, not `qwen3:8b` | qwen3:8b (5.2 GB) plus bge-m3 (1.2 GB) does not fit in 6 GB of VRAM. |
| 2026-11-08 | Answer model `qwen3:4b-instruct-2507`, replacing `qwen3.5:4b` | Dev bake-off, judge `gpt-oss:120b`: answer accuracy 0.789 ±0.130 against 0.737 ±0.140, false refusals 0.053 against 0.105, p95 10.0 s against 7.3 s (`results/golden-20261108-093837.jsonl`, `results/golden-20261108-093404.jsonl`). The accuracy gap is within the intervals; it was picked on accuracy and false refusals. `granite4.1:3b` refused 97% of answerable questions under the same prompt (`results/golden-20261108-094348.jsonl`). |
| 2026-11-08 | Keep `qwen3:4b-instruct-2507` after its test run | On test it scored 0.776 ±0.089 against qwen3.5:4b's 0.847 (`results/golden-20261108-094833.summary.json`, `results/golden-20261108-001902.summary.json`), the reverse of the dev result; both gaps are within the intervals. Switching back because of the test score would select a model on the test set, so the dev choice stands. A 38-item dev split cannot separate two near-equal models. |
| 2026-11-08 | Keep `gpt-oss:120b` as judge | On the three worked examples in GUIDELINES.md it gave the right verdicts and was the fastest of the free Ollama Cloud models tried; nemotron-3-super and -ultra were also right but slower, and nemotron-3-nano returned invalid JSON. A spot check, not a results file. |
| 2026-11-07 | 8K context for the answer model, not 16K | At 16K, Ollama put 16% of the model on the CPU next to bge-m3; at 8K it runs fully on the GPU (3.3 GB). Prompts on dev were 1.4K to 4.5K tokens. |
| 2026-11-07 | Answer prompt: every sentence cited, refusals start with a fixed sentence | A dev pass with the first prompt showed answers with no citations and refusals in free wording, which the refusal check misses. The revised prompt fixed the citations; some near-miss refusals are still free-worded (see Limitations). |
| 2026-11-07 | Judge from a different model family than the answer model | Same-family judges favour their own outputs. |
| 2026-11-08 | Judge `gpt-oss:120b` on Ollama Cloud, not Gemini | Gemini's free tier caps `gemini-3.6-flash` at 20 requests per day per model, and one golden run needs about 85 judge calls. `gemini-3.8-flash` and `3.7-flash` accepted requests but returned nothing within 45 to 90 seconds. |
| 2026-11-07 | Golden and attack items carry a `dev`/`test` split | Prompts and thresholds are tuned on `dev`; reported numbers come from `test` only. |
| 2026-11-07 | Keyword search ORs the question's lexemes instead of using `websearch_to_tsquery` | On dev (n=38), AND semantics returned no rows for 92% of questions and keyword recall@5 was 0.079 (`results/retrieval-20261107-230923.json`). ORed lexemes: 0% empty, recall@5 0.421 (`results/retrieval-20261107-230946.json`). |
| 2026-11-07 | Keyword search is in-memory BM25, replacing `ts_rank_cd` | `ts_rank_cd` has no IDF, so common words outweigh rare ones. On dev, BM25 raised keyword recall@5 from 0.421 to 0.789 (`results/retrieval-20261107-231512.json`). |
| 2026-11-07 | Keep hybrid retrieval, not dense only | On dev (n=38) dense scored 0.895 recall@5 against hybrid's 0.868, one question apart. Hybrid was kept because the golden questions avoid the sheets' wording by design, and real users often type exact terms. Decided before the test split was run; on test (n=85) hybrid scored 0.906 against dense's 0.812. |

## Results

| Run | Defenses | recall@5 | MRR | Answer acc. | Refusal acc. | Attack success | p95 latency | $/1k queries |
|---|---|---|---|---|---|---|---|---|
| golden-20261108-001902 (qwen3.5:4b) | none | 0.906 | 0.733 | 84.7% | 100% | | 16.8 s | $0 (local) |
| golden-20261108-094833 (qwen3:4b-instruct-2507) | none | 0.906 | 0.733 | 77.6% ±8.9 | 95.5% ±8.7 | | 10.8 s | $0 (local) |
