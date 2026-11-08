.PHONY: setup models db corpus ingest serve test lint eval-retrieval eval-golden eval-grounding eval-attacks

setup: ; uv sync
models:
	ollama pull bge-m3
	ollama pull qwen3:4b-instruct-2507-q4_K_M
	ollama create qwen3-4b-instruct-8k -f ollama/Modelfile
db: ; docker compose up -d db
# Pinned so evidence quotes in data/golden.jsonl keep matching. Bump deliberately and re-run the quote test.
CORPUS_COMMIT = 757270a26306e5edda9957bb7f86cfcde03c30f9
corpus:
	test -d data/corpus || ( git init -q data/corpus \
	  && git -C data/corpus fetch -q --depth 1 https://github.com/OWASP/CheatSheetSeries $(CORPUS_COMMIT) \
	  && git -C data/corpus checkout -q FETCH_HEAD )
ingest: ; uv run python -m owasp_rag.ingest data/corpus/cheatsheets
serve: ; uv run uvicorn owasp_rag.api:app --reload
test: ; uv run pytest
lint: ; uv run ruff check . && uv run ruff format --check .
eval-retrieval: ; uv run python -m owasp_rag.evals retrieval
eval-golden: ; uv run python -m owasp_rag.evals golden
# Usage: make eval-grounding RUN=results/golden-<stamp>.jsonl
eval-grounding: ; uv run --group ml python -m owasp_rag.evals grounding $(RUN)
eval-attacks: ; uv run --group ml python -m owasp_rag.evals attacks
