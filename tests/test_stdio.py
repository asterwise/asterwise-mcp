"""The stdio entry point starts, lists every tool, and refuses tool calls
without a key (the Glama hosted build test exercises exactly this)."""

import os
import sys
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

ROOT = Path(__file__).resolve().parent.parent
STDIO = ROOT / "stdio.py"


def _transport(**env):
    base = {k: v for k, v in os.environ.items() if k != "ASTERWISE_API_KEY"}
    base.update(env)
    return PythonStdioTransport(str(STDIO), python_cmd=sys.executable, env=base, cwd=str(ROOT))


@pytest.mark.asyncio
async def test_stdio_lists_all_tools_without_a_key():
    async with Client(_transport()) as c:
        tools = await c.list_tools()
    names = {t.name for t in tools}
    assert len(tools) >= 100
    assert "asterwise_get_natal_chart" in names
    assert all(t.description for t in tools)


@pytest.mark.asyncio
async def test_stdio_tool_call_without_key_names_the_env_var():
    async with Client(_transport()) as c:
        try:
            result = await c.call_tool(
                "asterwise_get_number_meaning", {"number": 7}, raise_on_error=False
            )
            text = " ".join(getattr(b, "text", "") for b in result.content)
            assert result.is_error
        except Exception as exc:  # older client versions raise instead
            text = str(exc)
    assert "ASTERWISE_API_KEY" in text
