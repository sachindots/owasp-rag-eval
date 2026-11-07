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


# Edge cases found in the pinned corpus.


def test_inline_code_line_with_triple_backticks_is_not_a_fence():
    # Authorization_Cheat_Sheet.md writes a whole line of inline code with ``` on both ends.
    sheet = "# T\n\n## A\n\n```https://bank.example/acct?id=901```\n\n## B\n\nAfter.\n"
    chunks = split_markdown("T", sheet)
    assert [c.heading for c in chunks] == ["T > A", "T > B"]


def test_indented_fence_in_a_list_hides_hash_lines_and_survives_blank_lines():
    sheet = (
        "# T\n\n- step one:\n\n    ```bash\n    # install\n\n    pip install x\n    ```\n\n"
        "## Next\n\nDone.\n"
    )
    chunks = split_markdown("T", sheet, max_chars=40)
    fence = next(c for c in chunks if "# install" in c.text)
    assert "pip install x" in fence.text
    assert fence.heading == "T"
    assert chunks[-1].heading == "T > Next"


def test_tilde_fence_closes_only_on_tildes():
    sheet = "# T\n\n~~~\n```\n# not a heading\n~~~\n\n## After\n\nx\n"
    chunks = split_markdown("T", sheet)
    assert [c.heading for c in chunks] == ["T", "T > After"]
    assert "# not a heading" in chunks[0].text


def test_heading_markup_is_cleaned_in_the_path():
    sheet = "# T\n\n### Rule \\#1 - use [`HttpOnly`](https://example.com) cookies\n\nBody.\n"
    assert split_markdown("T", sheet)[0].heading == "T > Rule #1 - use HttpOnly cookies"


def test_oversized_fence_stays_whole():
    code = "\n\n".join(f"line{i} = {i}" for i in range(40))
    sheet = f"# T\n\nIntro.\n\n```python\n{code}\n```\n\nOutro.\n"
    chunks = split_markdown("T", sheet, max_chars=100)
    fence = next(c for c in chunks if "line0" in c.text)
    assert "line39" in fence.text
    assert fence.text.count("```") == 2


def test_heading_path_pops_back_to_shallower_level():
    sheet = "# T\n\n## A\n\n### A1\n\nx\n\n## B\n\ny\n"
    assert [c.heading for c in split_markdown("T", sheet)] == ["T > A > A1", "T > B"]
