#!/usr/bin/env python3
"""
Export one docs page per MCP tool into the asterwise-docs checkout.

The description sent to MCP clients is the compact form (see
runtime.compact_description); the full text with output and error contracts
lives in runtime.FULL_TOOL_DESCRIPTIONS and is rendered here as MDX.

    python scripts/export_tool_docs.py                # write to ../asterwise-docs
    python scripts/export_tool_docs.py --check        # exit 1 if pages differ
    python scripts/export_tool_docs.py --docs-root /path/to/asterwise-docs
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("ASTERWISE_API_BASE_URL", "https://api.asterwise.com")
os.environ.setdefault("JWT_SECRET", "x" * 40)

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from fastmcp import Client  # noqa: E402

from runtime import FULL_TOOL_DESCRIPTIONS, tool_doc_url  # noqa: E402
from server import mcp  # noqa: E402

SECTION_ORDER = [
    "WHAT THIS TOOL COVERS", "WORKFLOW", "INPUT CONTRACT", "OUTPUT CONTRACT",
    "RESPONSE FORMAT", "COMPUTE CLASS", "ERROR CONTRACT", "DO NOT CONFUSE WITH",
]
TITLES = {
    "WHAT THIS TOOL COVERS": "What it covers", "WORKFLOW": "Workflow",
    "INPUT CONTRACT": "Input", "OUTPUT CONTRACT": "Output contract",
    "RESPONSE FORMAT": "Response format", "COMPUTE CLASS": "Compute class",
    "ERROR CONTRACT": "Errors", "DO NOT CONFUSE WITH": "Do not confuse with",
}


def slug_for(name: str) -> str:
    return name.removeprefix("asterwise_").replace("_", "-")


def split_sections(full: str) -> tuple[str, dict[str, str]]:
    parts = re.split(r"\n\s*SECTION: ([A-Z][A-Z ]*(?:\([^)\n]*\))?)\s*\n", "\n\n" + full)
    lead = parts[0].strip()
    sections: dict[str, str] = {}
    for i in range(1, len(parts) - 1, 2):
        title = parts[i].strip()
        key = title.split(" (")[0]
        qualifier = title[len(key):].strip()
        body = parts[i + 1].strip()
        if qualifier:
            body = f"**{qualifier.strip('()')}**  \n{body}"
        sections[key] = (sections[key] + "\n\n" + body) if key in sections else body
    return lead, sections


def _mdx_escape(text: str) -> str:
    # MDX treats { } and < > as JSX; keep prose literal.
    return text.replace("{", "&#123;").replace("}", "&#125;").replace("<", "&lt;").replace(">", "&gt;")


def schema_table(schema: dict) -> str:
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    rows = ["| Parameter | Type | Required | Description |", "|---|---|---|---|"]
    for name, p in props.items():
        typ = p.get("type") or ("object" if "properties" in p else "/".join(b.get("type", "?") for b in p.get("anyOf", [])) or "?")
        if "enum" in p:
            typ = "enum: " + ", ".join(f"`{v}`" for v in p["enum"])
        desc = p.get("description", "")
        if "properties" in p:
            inner = ", ".join(f"`{k}`{'*' if k in set(p.get('required', [])) else ''}" for k in p["properties"])
            desc = (desc + " Fields: " + inner).strip()
        # One table row per parameter: a line break or pipe inside a cell
        # (multi-line model docstrings) would end the row and break the table.
        cell = " ".join(desc.split()).replace("|", "\\|")
        rows.append(f"| `{name}` | {typ} | {'yes' if name in required else 'no'} | {_mdx_escape(cell)} |")
    return "\n".join(rows)


META_DESCRIPTION_MIN = 50
META_DESCRIPTION_MAX = 160
# ". " after these is not a sentence end.
_ABBREVIATIONS = ("e.g", "i.e", "etc", "vs", "approx", "incl", "no", "ch")


def meta_description(lead: str) -> str:
    """The page's <meta name="description">: 50-160 characters, whole words.

    Whole sentences of the tool's lead paragraph are added while they fit;
    a first sentence over 160 characters is cut at a word with an ellipsis.
    It used to be the first sentence cut at 150 characters, mid-word for 27
    tools (Grok SEO watch 2026-10-08). tests/test_tool_docs_meta.py holds
    every tool to 50-160 with no cut.
    """
    text_in = " ".join(lead.split())
    parts: list[str] = []
    start = 0
    for match in re.finditer(r"\. ", text_in):
        idx = match.start()
        if text_in[start:idx].lower().endswith(_ABBREVIATIONS):
            continue
        parts.append(text_in[start : idx + 1])
        start = idx + 2
    if text_in[start:].strip():
        parts.append(text_in[start:].strip())
    text = ""
    for sentence in parts:
        candidate = f"{text} {sentence}".strip()
        if len(candidate) > META_DESCRIPTION_MAX:
            break
        text = candidate
        if len(text) >= META_DESCRIPTION_MAX - 40:
            break
    if not text and parts:
        cut = parts[0][: META_DESCRIPTION_MAX - 1]
        text = cut[: cut.rfind(" ")].rstrip(" ,;:—-") + "…"
    return text


def render_page(tool: dict, full: str) -> str:
    lead, sections = split_sections(full)
    slug = slug_for(tool["name"])
    out = [
        "---",
        f"id: {slug}",
        f"title: {json.dumps(tool['title'] or tool['name'])}",
        f"description: {json.dumps(meta_description(lead))}",
        "hide_table_of_contents: false",
        "---",
        "",
        "{/* AUTO-GENERATED by asterwise-mcp/scripts/export_tool_docs.py. Do not edit. */}",
        "",
        f"`{tool['name']}`",
        "",
        _mdx_escape(lead),
        "",
        "## Parameters",
        "",
        schema_table(tool["inputSchema"]),
    ]
    for key in SECTION_ORDER:
        body = sections.get(key)
        if not body:
            continue
        out += ["", f"## {TITLES[key]}", "", _mdx_escape(body).replace("\n", "  \n")]
    out += ["", "## Connect", "",
            "Remote MCP endpoint: `https://mcp.asterwise.com/mcp`. Authenticate with `Authorization: Bearer <API key>` or OAuth. See the [MCP setup guide](/guides/mcp-setup).", ""]
    return "\n".join(out)


# Index grouping by tool name. The first matching rule wins; anything
# unmatched is Vedic astrology, the largest family.
_INDEX_GROUPS: list[tuple[str, tuple[str, ...]]] = [
    ("Western astrology", ("western",)),
    ("Horoscopes", ("horoscope",)),
    ("Tarot", ("tarot",)),
    ("Crystals", ("crystal",)),
    ("Dream symbols", ("dream",)),
    ("Numerology", (
        "numerology", "life_path", "expression_number", "soul_urge", "personality_number",
        "maturity_number", "balance_number", "karmic", "lo_shu", "chaldean", "personal_year",
        "personal_cycles", "lucky_numbers", "name_correction", "business_name", "number_meaning",
        "mobile_number", "vehicle_number", "angel_number", "biorhythm",
    )),
]
_INDEX_DEFAULT_GROUP = "Vedic astrology"


def index_group(name: str) -> str:
    for label, needles in _INDEX_GROUPS:
        if any(n in name for n in needles):
            return label
    return _INDEX_DEFAULT_GROUP


def render_index(tools: list[dict]) -> str:
    order = [_INDEX_DEFAULT_GROUP] + [label for label, _ in _INDEX_GROUPS]
    groups: dict[str, list[dict]] = {label: [] for label in order}
    for t in sorted(tools, key=lambda t: t["name"]):
        groups[index_group(t["name"])].append(t)
    description = (
        f"All {len(tools)} Asterwise MCP tools for Claude, Cursor and any MCP client, grouped by "
        "domain: Vedic and Western astrology, numerology, tarot, crystals and dreams."
    )
    assert len(description) <= 160, len(description)
    lines = ["---", "id: index", "title: \"MCP tools\"", f"description: {json.dumps(description)}", "slug: /mcp/tools/", "---", "",
             f"The Asterwise MCP server exposes {len(tools)} read-only tools. Each page lists the parameters, the output contract and the errors a tool can return.", "",
             "{/* AUTO-GENERATED by asterwise-mcp/scripts/export_tool_docs.py. Do not edit. */}"]
    for label in order:
        group = groups[label]
        if not group:
            continue
        lines += ["", f"## {label} ({len(group)})", "", "| Tool | Summary |", "|---|---|"]
        for t in group:
            lead, _ = split_sections(FULL_TOOL_DESCRIPTIONS[t["name"]])
            lines.append(f"| [{t['name']}](./{slug_for(t['name'])}) | {_mdx_escape(lead.split('. ')[0])} |")
    return "\n".join(lines) + "\n"


async def load_tools() -> list[dict]:
    async with Client(mcp) as c:
        return [t.model_dump(mode="json") for t in await c.list_tools()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs-root", type=Path, default=REPO_ROOT.parent / "asterwise-docs")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    out_dir = args.docs_root / "docs" / "mcp" / "tools"
    tools = asyncio.run(load_tools())
    pages = {out_dir / f"{slug_for(t['name'])}.mdx": render_page(t, FULL_TOOL_DESCRIPTIONS[t["name"]]) for t in tools}
    pages[out_dir / "index.mdx"] = render_index(tools)
    pages[out_dir / "_category_.json"] = json.dumps({"label": "MCP tools", "position": 90, "link": {"type": "doc", "id": "mcp/tools/index"}}, indent=2) + "\n"
    if args.check:
        drift = [str(p) for p, content in pages.items() if not p.is_file() or p.read_text() != content]
        extra = [str(p) for p in out_dir.glob("*.mdx") if p not in pages] if out_dir.is_dir() else []
        if drift or extra:
            print("DRIFT:", *drift, *extra, sep="\n  ")
            return 1
        print(f"{len(pages)} tool doc pages match.")
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for p, content in pages.items():
        p.write_text(content)
    for p in out_dir.glob("*.mdx"):
        if p not in pages:
            p.unlink()
    print(f"wrote {len(pages)} files to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
