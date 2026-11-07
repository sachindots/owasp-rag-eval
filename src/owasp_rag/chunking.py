from .schemas import Chunk


def split_markdown(doc: str, markdown: str, max_chars: int = 2000) -> list[Chunk]:
    """Split one cheat sheet into chunks along its headings.

    Contract (tests/test_chunking.py checks it):
    - Every chunk has `doc=doc` and `id=f"{doc}#{n}"`, n counting from 0 in document order.
    - `heading` is the path of headings above the chunk, joined with " > ", for example
      "SQL Injection Prevention Cheat Sheet > Primary Defenses". Text before the first
      heading gets heading "".
    - Heading lines are not part of `text`. Every other non-blank line lands in some chunk.
    - A section longer than `max_chars` is split on blank lines, so no chunk exceeds
      `max_chars` unless a single paragraph does on its own.
    - A "#" line inside a ``` code fence is code, not a heading, and a fence is never split.
    - Sections with no body text produce no chunk.
    """
    raise NotImplementedError
