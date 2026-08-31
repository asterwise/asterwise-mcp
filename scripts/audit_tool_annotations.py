#!/usr/bin/env python3
"""Audit FastMCP tool annotations for OpenAI Apps submission readiness.

Fails (exit 1) if any tool is missing title, or if annotations are not exactly:
  readOnlyHint=True, openWorldHint=False, destructiveHint=False
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Repo root on sys.path when run as scripts/audit_tool_annotations.py
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _ann_val(annotations: object | None, key: str) -> object | None:
    if annotations is None:
        return None
    if isinstance(annotations, dict):
        return annotations.get(key)
    return getattr(annotations, key, None)


async def _run() -> int:
    from server import mcp

    tools = await mcp.list_tools()
    rows: list[tuple[str, bool, object, object, object, int]] = []
    failures: list[str] = []

    for tool in tools:
        name = tool.name
        title = getattr(tool, "title", None)
        has_title = bool(title and str(title).strip())
        ann = tool.annotations
        read_only = _ann_val(ann, "readOnlyHint")
        open_world = _ann_val(ann, "openWorldHint")
        destructive = _ann_val(ann, "destructiveHint")
        desc = tool.description or ""
        rows.append((name, has_title, read_only, open_world, destructive, len(desc)))

        if not has_title:
            failures.append(f"{name}: missing title")
        if read_only is not True:
            failures.append(f"{name}: readOnlyHint={read_only!r} (expected True)")
        if open_world is not False:
            failures.append(
                f"{name}: openWorldHint={open_world!r} (expected False explicitly)"
            )
        if destructive is not False:
            failures.append(
                f"{name}: destructiveHint={destructive!r} (expected False explicitly)"
            )

    headers = (
        "name",
        "has_title",
        "readOnlyHint",
        "openWorldHint",
        "destructiveHint",
        "desc_len",
    )
    widths = [len(h) for h in headers]
    str_rows = [
        (
            r[0],
            str(r[1]),
            str(r[2]),
            str(r[3]),
            str(r[4]),
            str(r[5]),
        )
        for r in rows
    ]
    for row in str_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(row: tuple[str, ...]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    print(fmt(headers))
    print(fmt(tuple("-" * w for w in widths)))
    for row in sorted(str_rows, key=lambda r: r[0]):
        print(fmt(row))
    print()
    print(f"tools={len(rows)} failures={len(failures)}")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OK: all tools have title and required annotations.")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
