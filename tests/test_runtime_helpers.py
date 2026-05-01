"""format_tool_result, structured_markdown, markdown helpers."""

from __future__ import annotations

from models import ResponseFormat
from runtime import format_tool_result, structured_markdown


def test_format_tool_result_json() -> None:
    out = format_tool_result({"x": 1}, ResponseFormat.JSON, lambda d: "md")
    assert '"x": 1' in out


def test_format_tool_result_markdown() -> None:
    out = format_tool_result({"a": 1}, ResponseFormat.MARKDOWN, lambda d: "## Hi")
    assert out == "## Hi"


def test_structured_markdown_nested() -> None:
    md = structured_markdown(
        "T",
        {
            "flag": True,
            "n": 0,
            "nested": {"k": "v"},
            "items": [1, {"a": 2}],
            "empty": [],
        },
    )
    assert "## T" in md
    assert "Yes" in md
    assert "Nested" in md or "nested" in md.lower()
    assert "empty" in md.lower() or "(empty)" in md
