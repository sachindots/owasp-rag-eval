.PHONY: setup db corpus ingest serve test lint eval-golden eval-attacks

setup: ; uv sync
db: ; docker compose up -d db
corpus: ; test -d data/corpus || git clone --depth 1 https://github.com/OWASP/CheatSheetSeries data/corpus
ingest: ; uv run python -m owasp_rag.ingest data/corpus/cheatsheets
serve: ; uv run uvicorn owasp_rag.api:app --reload
test: ; uv run pytest
lint: ; uv run ruff check . && uv run ruff format --check .
eval-golden: ; uv run python -m owasp_rag.evals golden
eval-attacks: ; uv run python -m owasp_rag.evals attacks
