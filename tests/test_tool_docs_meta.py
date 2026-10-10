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
    assert len(TOOLS) == 104


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
