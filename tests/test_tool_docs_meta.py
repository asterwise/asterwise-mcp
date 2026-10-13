"""Every MCP tool docs page gets a title and description search engines keep.

scripts/export_tool_docs.py writes docs.asterwise.com/mcp/tools/<tool>/;
the <title> is "<tool title> | Asterwise Docs" and the description comes
from the tool's lead paragraph. Grok's SEO watch (2026-10-08..10) found
descriptions of 30-35 characters and 27 cut mid-word at 150.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("export_tool_docs", ROOT / "scripts" / "export_tool_docs.py")
exporter = importlib.util.module_from_spec(_spec)
sys.modules["export_tool_docs"] = exporter
_spec.loader.exec_module(exporter)

from runtime import FULL_TOOL_DESCRIPTIONS  # noqa: E402

TOOLS = sorted(FULL_TOOL_DESCRIPTIONS)


def test_every_tool_is_covered():
    assert len(TOOLS) == 118


@pytest.mark.parametrize("name", TOOLS)
def test_description_is_whole_sentences_within_bounds(name):
    lead, _ = exporter.split_sections(FULL_TOOL_DESCRIPTIONS[name])
    text = exporter.meta_description(lead)
    assert exporter.META_DESCRIPTION_MIN <= len(text) <= exporter.META_DESCRIPTION_MAX, text
    assert not text.endswith("…"), text


@pytest.mark.parametrize("name", TOOLS)
def test_title_fits(name):
    from server import mcp

    tool = mcp._local_provider._components
    titles = {c.name: (getattr(c, "title", None) or c.name) for c in tool.values() if hasattr(c, "fn")}
    assert len(titles[name] + " | Asterwise Docs") <= 60, titles[name]


def _input_schemas() -> dict:
    import asyncio

    from fastmcp import Client
    from server import mcp

    async def _load():
        async with Client(mcp) as c:
            return {t.name: t.inputSchema for t in await c.list_tools()}
    return asyncio.run(_load())


INPUT_SCHEMAS = _input_schemas()


@pytest.mark.parametrize("name", TOOLS)
def test_parameter_table_has_no_markdown_emphasis(name):
    # Grok 2026-10-13: `lat`*, `lon`* rendered as italics with a stray "*".
    table = exporter.schema_table(INPUT_SCHEMAS[name])
    assert "`*" not in table, table


def test_nested_fields_are_listed_as_required_and_optional():
    schema = {"properties": {"request": {"type": "object", "properties": {"a": {}, "b": {}, "c": {}}, "required": ["a", "c"]}}}
    row = exporter.schema_table(schema).splitlines()[-1]
    assert "Required fields: `a`, `c`." in row and "Optional fields: `b`." in row, row


@pytest.mark.parametrize("name", [n for n in TOOLS if set(INPUT_SCHEMAS[n].get("properties", {})) <= {"response_format"}])
def test_no_input_tools_promise_no_input_errors(name):
    # Grok 2026-10-13: a no-input lookup listed BirthData and date-range errors.
    _, sections = exporter.split_sections(FULL_TOOL_DESCRIPTIONS[name])
    errors = sections.get("ERROR CONTRACT", "")
    for word in ("BirthData", "date", "timezone", "range", "validation failures"):
        assert word not in errors, (name, errors)


@pytest.mark.parametrize("name", [n for n in TOOLS if "days" not in INPUT_SCHEMAS[n].get("properties", {})])
def test_single_day_tools_do_not_promise_range_errors(name):
    _, sections = exporter.split_sections(FULL_TOOL_DESCRIPTIONS[name])
    assert "range over 31 days" not in sections.get("ERROR CONTRACT", ""), name
