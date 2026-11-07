# OWASP Cheat Sheet Assistant

> Placeholder. Rewrite this README in your own words before you publish the repo.

A RAG assistant over the [OWASP Cheat Sheet Series](https://github.com/OWASP/CheatSheetSeries), with evals for answer quality and for prompt-injection resistance. The work plan is in [PLAN.md](PLAN.md).

## Run it locally

Needs Docker, [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com) (`ollama pull qwen3:8b bge-m3`).

```bash
cp .env.example .env
make setup db corpus
make ingest
make test
make serve
make eval-golden
make eval-attacks
```

## License

The cheat sheet text, and the quotes from it in `data/`, are © OWASP Foundation under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Pick a license for the code and add a LICENSE file.
