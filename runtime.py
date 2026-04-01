"""Tool runtime: MCP errors, auth, formatting, validation helpers."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, NoReturn

from fastmcp.server.dependencies import get_http_request
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, INTERNAL_ERROR, ErrorData, ToolAnnotations
from pydantic import ValidationError

from auth import validate_and_get_key
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


def tool_error(message: str, code: int = INTERNAL_ERROR) -> NoReturn:
    """
    Raise a proper MCP protocol error.
    This function never returns — it always raises.
    Use for upstream API errors, unexpected failures.
    """
    raise McpError(ErrorData(code=code, message=message))


def invalid_params(message: str) -> NoReturn:
    """
    Raise MCP invalid params error.
    This function never returns — it always raises.
    Use for bad input detected before calling upstream.
    """
    raise McpError(ErrorData(code=INVALID_PARAMS, message=message))


def raise_validation_error(exc: ValidationError) -> NoReturn:
    """Convert Pydantic ValidationError to MCP invalid_params."""
    first = exc.errors()[0]
    loc = first.get("loc", ())
    field = " -> ".join(str(x) for x in loc)
    msg = first.get("msg", "")
    invalid_params(f"Invalid '{field}': {msg}")


def unexpected_tool_error(tool_name: str, exc: BaseException) -> NoReturn:
    """Unexpected exception inside a tool handler."""
    tool_error(
        f"Unexpected error in {tool_name}: {type(exc).__name__}: {exc}"
    )


async def require_api_key() -> str:
    """Validate HTTP auth and return the Asterwise API key."""
    req = get_http_request()
    return validate_and_get_key(dict(req.headers))


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
