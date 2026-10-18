"""OpenAI app review: every tool's hints are explicit booleans and match what
the tool does (rejection 2026-09-15 was for annotations). Runs the same check
as scripts/audit_tool_annotations.py."""
import asyncio

from scripts.audit_tool_annotations import OPEN_WORLD_TOOLS, _run


def test_every_tool_has_explicit_annotations_matching_behaviour():
    assert asyncio.run(_run()) == 0


def test_geocode_is_the_only_open_world_tool():
    from server import mcp

    tools = asyncio.run(mcp.list_tools())
    open_world = {t.name for t in tools if t.annotations.openWorldHint is True}
    assert open_world == set(OPEN_WORLD_TOOLS) == {"asterwise_geocode"}
