"""The description sent to clients must stay compact and point at the docs page."""
from __future__ import annotations

import asyncio
import json

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
    assert len(tools) == 103
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
