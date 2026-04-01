"""Shared tool runtime: auth, response formatting, MCP annotations."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from fastmcp.server.dependencies import get_http_request
from mcp.types import ToolAnnotations

from auth import validate_and_get_key
from errors import AsterwiseMCPError
from models import ResponseFormat

STANDARD_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)

REPORT_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)


async def require_api_key() -> str:
    """Validate HTTP auth and return the Asterwise API key."""
    return validate_and_get_key(get_http_request())


def format_tool_result(
    data: dict[str, Any],
    response_format: ResponseFormat,
    to_markdown: Callable[[dict[str, Any]], str],
) -> str:
    """Return JSON or markdown per tool contract."""
    if response_format == ResponseFormat.JSON:
        return json.dumps(data, indent=2, default=str)
    return to_markdown(data)


def structured_markdown(title: str, data: dict[str, Any]) -> str:
    """Readable markdown for arbitrary nested API payloads."""
    lines = [f"## {title}", ""]
    lines.append(_md_value(data))
    return "\n".join(lines)


def _md_value(obj: Any, depth: int = 0) -> str:
    indent = "  " * depth
    if obj is None:
        return "*null*"
    if isinstance(obj, bool):
        return "Yes" if obj else "No"
    if isinstance(obj, (int, float, str)):
        return str(obj)
    if isinstance(obj, dict):
        parts: list[str] = []
        for k, v in obj.items():
            label = str(k).replace("_", " ").title()
            if isinstance(v, (dict, list)):
                parts.append(f"{indent}- **{label}**")
                parts.append(_md_value(v, depth + 1))
            else:
                parts.append(f"{indent}- **{label}**: {_md_value(v, depth)}")
        return "\n".join(parts)
    if isinstance(obj, list):
        if not obj:
            return f"{indent}*(empty)*"
        parts = []
        for i, item in enumerate(obj):
            if isinstance(item, dict):
                parts.append(f"{indent}- **Item {i + 1}**")
                parts.append(_md_value(item, depth + 1))
            else:
                parts.append(f"{indent}- {_md_value(item, depth)}")
        return "\n".join(parts)
    return str(obj)


def mcp_error_message(exc: BaseException) -> str:
    """User-facing error string for tool results."""
    if isinstance(exc, AsterwiseMCPError):
        base = str(exc)
        if getattr(exc, "hint", None):
            return f"{base}\n\nNext step: {exc.hint}"
        return base
    return (
        f"{type(exc).__name__}: {exc}\n\n"
        "Retry with corrected parameters or check Asterwise API status."
    )
