"""The description sent to clients must stay compact and point at the docs page."""
from __future__ import annotations

import asyncio
import json
import re

from fastmcp import Client

from runtime import FULL_TOOL_DESCRIPTIONS, tool_doc_url
from server import mcp

MAX_DESCRIPTION_CHARS = 3_300
MAX_TOOLS_LIST_BYTES = 260 * 1024


def _tools():
    async def _load():
        async with Client(mcp) as c:
            return [t.model_dump(mode="json") for t in await c.list_tools()]
    return asyncio.run(_load())


def test_every_description_is_compact_and_links_to_docs():
    tools = _tools()
    assert len(tools) == 104
    for t in tools:
        assert len(t["description"]) <= MAX_DESCRIPTION_CHARS, (t["name"], len(t["description"]))
        assert tool_doc_url(t["name"]) in t["description"], t["name"]
        assert "SECTION: OUTPUT CONTRACT" not in t["description"], t["name"]
        assert t["name"] in FULL_TOOL_DESCRIPTIONS, t["name"]


def test_tools_list_total_size_is_bounded():
    total = sum(len(json.dumps(t)) for t in _tools())
    assert total <= MAX_TOOLS_LIST_BYTES, f"tools/list is {total/1024:.0f} KB"


def test_response_format_is_optional_everywhere():
    for t in _tools():
        assert "response_format" not in t["inputSchema"].get("required", []), t["name"]


def test_no_doubled_words_in_tool_text():
    # "the classical classical Vimshottari timeline" shipped on the dasha
    # tool and its docs page until 2026-10-04.
    doubled = re.compile(r"\b([A-Za-z]{2,})\s+\1\b", re.IGNORECASE)
    texts = dict(FULL_TOOL_DESCRIPTIONS)
    for t in _tools():
        texts[f"{t['name']} (schema)"] = json.dumps(t["inputSchema"])
    found = {name: m.group(0) for name, text in texts.items() if (m := doubled.search(text))}
    assert found == {}


def _section(text: str, name: str) -> str:
    m = re.search(r"SECTION: " + name + r"\n(.*?)(?=\nSECTION: |\Z)", text, re.S)
    return m.group(1) if m else ""


def _input_names(schema: dict) -> set[str]:
    names = set(schema.get("properties", {}))
    for prop in schema.get("properties", {}).values():
        names |= set(prop.get("properties", {}))  # fields inside birth, person1, ...
    for definition in schema.get("$defs", {}).values():
        names |= set(definition.get("properties", {}))
    return names


def test_output_contract_lines_name_their_field():
    # "(string — methodology note)" with no field name shipped on the Saham
    # and Harsha Bala tools until 2026-10-05; the API returns no such field.
    unnamed = re.compile(r"^\s*\((string|int|float|bool|array|object)\b")
    found = [
        (name, line)
        for name, text in FULL_TOOL_DESCRIPTIONS.items()
        for line in _section(text, "OUTPUT CONTRACT").splitlines()
        if unnamed.match(line)
    ]
    assert found == []


def test_input_contract_names_real_parameters():
    # The Saham and Harsha Bala tools documented "target_year (required int)"
    # while the tool parameter is year (sent upstream as target_year).
    found = []
    for t in _tools():
        allowed = _input_names(t["inputSchema"])
        for line in _section(FULL_TOOL_DESCRIPTIONS[t["name"]], "INPUT CONTRACT").splitlines():
            m = re.match(r"\s*([a-z_][a-z0-9_]*) \((required|optional)", line)
            if m and m.group(1) not in allowed:
                found.append((t["name"], m.group(1)))
    assert found == []
