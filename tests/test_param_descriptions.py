"""Every top-level tool parameter carries a description (directory quality gate)."""

from __future__ import annotations

import pytest
from fastmcp import Client


@pytest.mark.asyncio
async def test_every_tool_parameter_has_a_description() -> None:
    from server import mcp

    async with Client(mcp) as c:
        tools = await c.list_tools()
    assert len(tools) >= 100
    gaps = [
        (t.name, name)
        for t in tools
        for name, schema in (t.inputSchema.get("properties") or {}).items()
        if not str(schema.get("description", "")).strip()
    ]
    assert gaps == [], f"{len(gaps)} undescribed parameters, e.g. {gaps[:8]}"


def test_vocabulary_has_no_unused_overrides() -> None:
    import asyncio

    from fastmcp import Client

    from param_docs import TOOL_PARAM_DESCRIPTIONS
    from server import mcp

    async def _names() -> set[tuple[str, str]]:
        async with Client(mcp) as c:
            tools = await c.list_tools()
        return {
            (t.name, p)
            for t in tools
            for p in (t.inputSchema.get("properties") or {})
        }

    known = asyncio.run(_names())
    stale = [k for k in TOOL_PARAM_DESCRIPTIONS if k not in known]
    assert stale == [], f"overrides for parameters that no longer exist: {stale}"


def test_no_false_undescribed_warning_for_model_parameters() -> None:
    """describe_parameters must not report parameters whose description lives
    on the referenced model ($ref), which is what clients actually receive."""
    from param_docs import describe_parameters
    from server import mcp

    assert describe_parameters(mcp) == []


def test_described_resolves_refs_and_unions() -> None:
    from param_docs import _described

    defs = {
        "Birth": {"description": "Birth data.", "properties": {}},
        "Bare": {"properties": {}},
        "Loop": {"$ref": "#/$defs/Loop"},
    }
    assert _described({"description": "direct"}, defs)
    assert _described({"$ref": "#/$defs/Birth"}, defs)
    assert _described({"anyOf": [{"$ref": "#/$defs/Birth"}, {"type": "null"}]}, defs)
    assert _described({"allOf": [{"description": "via allOf"}]}, defs)
    assert not _described({"$ref": "#/$defs/Bare"}, defs)
    assert not _described({"$ref": "#/$defs/Loop"}, defs)  # recursion guard
    assert not _described({"type": "string"}, defs)
    assert not _described({"description": "   "}, defs)
    assert not _described(None, defs)
