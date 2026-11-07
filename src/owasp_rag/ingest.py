import argparse
from pathlib import Path

from .chunking import split_markdown
from .db import connect, init_schema, replace_chunks
from .llm import embed

BATCH = 64


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Chunk, embed and index the cheat sheets.")
    parser.add_argument("corpus_dir", type=Path)
    args = parser.parse_args(argv)

    paths = sorted(args.corpus_dir.glob("*.md"))
    if not paths:
        raise SystemExit(f"no .md files in {args.corpus_dir}; run `make corpus` first")

    chunks = [c for p in paths for c in split_markdown(p.stem, p.read_text(encoding="utf-8"))]
    embeddings: list[list[float]] = []
    for i in range(0, len(chunks), BATCH):
        embeddings += embed([f"{c.heading}\n\n{c.text}" for c in chunks[i : i + BATCH]])

    with connect() as conn:
        init_schema(conn)
        replace_chunks(conn, chunks, embeddings)
    print(f"indexed {len(chunks)} chunks from {len(paths)} cheat sheets")


if __name__ == "__main__":
    main()
