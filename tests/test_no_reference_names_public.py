"""Tool descriptions name no reference software or panchang website (founder 2026-10-26)."""
import re

import pytest
from fastmcp import Client

from runtime import FULL_TOOL_DESCRIPTIONS
from server import mcp

_NAMES = re.compile(r"drik panchang|drik's|drikpanchang|pyjhora|jagannatha|jhora", re.I)


@pytest.mark.asyncio
async def test_live_tool_list_names_no_reference_software():
    async with Client(mcp) as c:
        tools = await c.list_tools()
    text = " ".join((t.description or "") + str(t.inputSchema) for t in tools)
    assert _NAMES.findall(text) == []


def test_full_descriptions_name_no_reference_software():
    assert [n for n, d in FULL_TOOL_DESCRIPTIONS.items() if _NAMES.search(d)] == []
