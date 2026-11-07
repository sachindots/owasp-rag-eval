# Instructions for coding agents

Read PLAN.md (the milestones) and GUIDELINES.md (the labelling rubric) before you change anything. Work one PLAN.md checkbox at a time, and finish it before starting the next.

## Commands

- `uv sync` installs everything.
- `make db corpus ingest` starts Postgres, downloads the cheat sheets and indexes them.
- `uv run pytest` runs the tests. `uv run ruff check . && uv run ruff format --check .` runs lint.
- `make eval-golden` and `make eval-attacks` run the evals and write `results/*.jsonl`.

## How the code is laid out

- The stubs that raise `NotImplementedError` are the work: `chunking.py`, `retrieval.py`, `answer.py`, `defenses.py`, `tools.authorize`, `evals/judge.py`, `evals/metrics.py`.
- `tests/` holds the spec for each stub. A test reports xfail until its stub exists. Make the tests pass. Never weaken, skip or delete a spec test to get there.
- `schemas.py` holds the data contracts. Change a schema only when the change is required, and update every caller and test in the same change.

## Rules

- Never write or edit items in `data/golden.jsonl`, `data/attacks.jsonl` or `data/human_labels.jsonl` unless the user dictates the exact content. A test set written by the same tool that writes the system makes the eval circular.
- Every number in README.md or PLAN.md must come from a results file a real run produced. Never type a metric by hand, round it favourably, or estimate it.
- Commit small, working steps with the real current date. Never set `GIT_AUTHOR_DATE` or `GIT_COMMITTER_DATE`, and never rewrite pushed history.
- Write commit messages, comments and docs as plain descriptions of the change. Do not mention AI tools or assistants anywhere.
- Do not add docs beyond README.md, PLAN.md and GUIDELINES.md. No blog posts, papers or build diaries.
- Secrets go in `.env`, which is gitignored. Never commit keys.
- At the end of each session, explain in chat what you changed and why, in plain language, so the user can explain it in an interview.
