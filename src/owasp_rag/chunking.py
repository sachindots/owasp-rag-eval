import re

from .schemas import Chunk

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
# Fences may be indented: the cheat sheets nest them inside list items.
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_ESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|])")


def _opens_fence(line: str) -> str | None:
    """The fence marker a line opens, or None. Per CommonMark, a backtick fence's info string
    holds no backticks, so a line of inline code like ```url``` is not a fence."""
    m = _FENCE.match(line)
    if not m or (m.group(1)[0] == "`" and "`" in m.group(2)):
        return None
    return m.group(1)


def _closes_fence(line: str, marker: str) -> bool:
    m = _FENCE.match(line)
    if not m or m.group(2).strip():
        return False
    return m.group(1)[0] == marker[0] and len(m.group(1)) >= len(marker)


def _clean_heading(title: str) -> str:
    return _ESCAPE.sub(r"\1", _LINK.sub(r"\1", title).replace("`", "")).strip()


def _sections(markdown: str) -> list[tuple[str, list[str]]]:
    """(heading path, body lines) for each heading, in document order, plus the preamble."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    path: list[str] = []
    fence: str | None = None
    for line in markdown.splitlines():
        if fence:
            if _closes_fence(line, fence):
                fence = None
        elif marker := _opens_fence(line):
            fence = marker
        elif m := _HEADING.match(line):
            level = len(m.group(1))
            path = path[: level - 1] + [_clean_heading(m.group(2))]
            sections.append((" > ".join(path), []))
            continue
        sections[-1][1].append(line)
    return sections


def _blocks(lines: list[str]) -> list[str]:
    """Paragraphs split on blank lines, keeping each fenced block whole."""
    blocks: list[str] = []
    current: list[str] = []
    fence: str | None = None
    for line in lines:
        if fence:
            current.append(line)
            if _closes_fence(line, fence):
                fence = None
        elif not line.strip():
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            fence = _opens_fence(line)
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def _pack(blocks: list[str], max_chars: int) -> list[str]:
    """Greedily join blocks with blank lines into pieces of at most max_chars. A block longer than
    max_chars becomes a piece of its own."""
    pieces: list[str] = []
    for block in blocks:
        if pieces and len(pieces[-1]) + 2 + len(block) <= max_chars:
            pieces[-1] += "\n\n" + block
        else:
            pieces.append(block)
    return pieces


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
    pieces = [
        (heading, text)
        for heading, lines in _sections(markdown)
        for text in _pack(_blocks(lines), max_chars)
    ]
    return [
        Chunk(id=f"{doc}#{n}", doc=doc, heading=heading, text=text)
        for n, (heading, text) in enumerate(pieces)
    ]
