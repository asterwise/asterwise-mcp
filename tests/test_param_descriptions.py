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


def test_no_description_contradicts_its_schema() -> None:
    """A parameter the schema requires must not advertise a default, and a
    tool's INPUT CONTRACT must not call an optional parameter required.
    Glama's scan caught both classes; these are agent-breaking inaccuracies."""
    import asyncio
    import re as _re

    from fastmcp import Client

    from server import mcp

    async def _tools():
        async with Client(mcp) as c:
            return await c.list_tools()

    tools = asyncio.run(_tools())
    promises_default, false_required = [], []
    for t in tools:
        schema = t.inputSchema or {}
        required = set(schema.get("required") or ())
        contract = ""
        if t.description and "INPUT CONTRACT:" in t.description:
            contract = t.description.split("INPUT CONTRACT:")[1].split("DO NOT CONFUSE")[0]
        for name, prop in (schema.get("properties") or {}).items():
            text = str((prop or {}).get("description") or "")
            if name in required and _re.search(
                r"Defaults?\s+to|when omitted|\(optional\)", text, _re.I
            ):
                promises_default.append((t.name, name))
            if name not in required and _re.search(
                rf"{_re.escape(name)}\s*[—:-]\s*Required", contract, _re.I
            ):
                false_required.append((t.name, name))
    assert promises_default == [], f"required parameters advertising a default: {promises_default}"
    assert false_required == [], f"optional parameters described as required: {false_required}"


def test_domain_specific_name_parameters_are_not_described_as_a_person() -> None:
    """`name` means a crystal or a dream symbol on these tools, not a person."""
    import asyncio

    from fastmcp import Client

    from server import mcp

    async def _tools():
        async with Client(mcp) as c:
            return {t.name: t for t in await c.list_tools()}

    tools = asyncio.run(_tools())
    for tool_name, expected in (
        ("asterwise_get_crystal", "crystal"),
        ("asterwise_get_dream_symbol", "dream symbol"),
    ):
        text = (tools[tool_name].inputSchema["properties"]["name"]["description"]).lower()
        assert expected in text, f"{tool_name}: {text!r}"
        assert "numerology" not in text, f"{tool_name} still uses the person-name text"
