from owasp_rag.chunking import split_markdown

SHEET = """\
# SQL Injection Prevention Cheat Sheet

## Introduction

SQL injection lets attackers change your queries.

## Primary Defenses

### Prepared Statements

Bind values through the database API.

```python
# this is a comment, not a heading
cur.execute("SELECT * FROM t WHERE id = %s", (user_id,))
```

## Empty Section

## References

See the OWASP site.
"""


def test_ids_doc_and_heading_paths():
    chunks = split_markdown("SQLi", SHEET)
    assert [c.id for c in chunks] == [f"SQLi#{n}" for n in range(len(chunks))]
    assert {c.doc for c in chunks} == {"SQLi"}
    headings = [c.heading for c in chunks]
    assert "SQL Injection Prevention Cheat Sheet > Introduction" in headings
    assert (
        "SQL Injection Prevention Cheat Sheet > Primary Defenses > Prepared Statements" in headings
    )
    assert not any(h.endswith("Empty Section") for h in headings)


def test_no_body_text_lost_and_no_heading_lines_in_text():
    chunks = split_markdown("SQLi", SHEET)
    joined = "\n".join(c.text for c in chunks)
    for line in SHEET.splitlines():
        is_heading = line.startswith("#") and not line.startswith("# this is")
        if line.strip() and not is_heading:
            assert line in joined, line
    assert "## Primary Defenses" not in joined


def test_hash_inside_code_fence_is_not_a_heading():
    chunks = split_markdown("SQLi", SHEET)
    fence = next(c for c in chunks if "cur.execute" in c.text)
    assert "# this is a comment, not a heading" in fence.text
    assert fence.text.count("```") == 2


def test_long_section_splits_on_blank_lines():
    paragraphs = [f"Paragraph {i} " + "x" * 80 for i in range(30)]
    sheet = "# Big\n\n" + "\n\n".join(paragraphs) + "\n"
    chunks = split_markdown("Big", sheet, max_chars=500)
    assert len(chunks) > 1
    assert all(len(c.text) <= 500 for c in chunks)
    assert all(c.heading == "Big" for c in chunks)
    joined = "\n".join(c.text for c in chunks)
    assert all(p in joined for p in paragraphs)


def test_text_before_first_heading():
    chunks = split_markdown("Pre", "Intro line.\n\n# Title\n\nBody.\n")
    assert chunks[0].heading == ""
    assert chunks[0].text.strip() == "Intro line."
