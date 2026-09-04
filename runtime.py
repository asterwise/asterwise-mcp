"""Tool runtime: MCP errors, auth, formatting, validation helpers."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any, NoReturn

from fastmcp import Context
from fastmcp.server.dependencies import get_http_headers
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS, INTERNAL_ERROR, ErrorData, ToolAnnotations
from pydantic import ValidationError

from auth import extract_api_key
from errors import AsterwiseMCPError, TokenExpiredError, TokenInvalidError
from models import ResponseFormat

logger = logging.getLogger("asterwise_mcp.runtime")

STANDARD_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

REPORT_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)

# Keys that must never appear in tool results (identity, infra, debugging).
_RESPONSE_LEAK_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "raw_key",
        "x_api_key",
        "key_id",
        "userid",
        "user_id",
        "account_id",
        "accountid",
        "request_id",
        "requestid",
        "engine_version",
        "engineversion",
        "sentry_id",
        "sentry_event_id",
        "sentryid",
        "traceback",
        "stack_trace",
        "stacktrace",
        "upstream_url",
        "upstreamurl",
        "internal_url",
        "internalurl",
    }
)


def scrub_tool_payload(obj: Any) -> Any:
    """Drop identity/infra leak keys from nested payloads; keep calculation fields."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if str(k).lower().replace("-", "_") in _RESPONSE_LEAK_KEYS:
                continue
            out[k] = scrub_tool_payload(v)
        return out
    if isinstance(obj, list):
        return [scrub_tool_payload(item) for item in obj]
    return obj


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
    """Unexpected exception inside a tool handler (no stack / internal detail leak)."""
    logger.exception(
        "unexpected_tool_error",
        extra={"tool": tool_name, "error_type": type(exc).__name__},
    )
    tool_error(
        f"Unexpected error in {tool_name}. Retry the request or check status.asterwise.com."
    )


class _ToolGuard:
    """See tool_guard()."""

    __slots__ = ("tool_name",)

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name

    async def __aenter__(self) -> "_ToolGuard":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if exc is None:
            return False
        if isinstance(exc, McpError):
            return False  # already a protocol error: propagate untouched
        if isinstance(exc, AsterwiseMCPError):
            tool_error(str(exc))
        if isinstance(exc, ValidationError):
            raise_validation_error(exc)
        if isinstance(exc, Exception):
            unexpected_tool_error(self.tool_name, exc)
        return False  # BaseException (cancellation etc.): propagate


def tool_guard(tool_name: str) -> _ToolGuard:
    """
    Error boundary shared by every tool handler.

    Use as ``async with tool_guard("asterwise_get_x"):`` around the handler
    body. Maps exceptions to MCP errors exactly as the historical per-tool
    try/except ladder did:

      McpError            -> re-raised as is
      AsterwiseMCPError   -> INTERNAL_ERROR with the upstream message
      ValidationError     -> INVALID_PARAMS naming the offending field
      any other Exception -> INTERNAL_ERROR "Unexpected error in <tool>",
                             logged with the traceback, no detail leaked
    """
    return _ToolGuard(tool_name)


async def require_api_key(ctx: Context | None = None) -> str:
    """
    Return the Asterwise API key for this request.

    Primary: ``get_http_headers()`` (FastMCP streamable HTTP).
    Secondary: ContextVar from ``APIKeyMiddleware``.
    Tertiary: ``ctx.request_context.request`` headers (stdio / tests).
    """
    from context import get_request_api_key

    api_key = None
    source: str | None = None

    try:
        headers = dict(
            get_http_headers(
                include={"authorization", "x-api-key"},
            )
        )
        headers_lower = {k.lower(): v for k, v in headers.items()}
        logger.debug(
            "auth_headers_received",
            extra={
                "header_keys": list(headers_lower.keys()),
                "has_authorization": "authorization" in headers_lower,
                "has_x_api_key": "x-api-key" in headers_lower,
            },
        )
        api_key = extract_api_key(headers_lower)
        if api_key:
            source = "http_headers"
    except (TokenExpiredError, TokenInvalidError) as e:
        raise McpError(
            ErrorData(code=INVALID_PARAMS, message=str(e))
        ) from e
    except Exception as e:
        logger.debug(
            "get_http_headers_failed",
            extra={"error": str(e)},
        )

    if not api_key:
        api_key = get_request_api_key()
        if api_key:
            source = "contextvar"

    if not api_key and ctx is not None:
        try:
            rc = ctx.request_context
            if rc and rc.request:
                headers = dict(rc.request.headers)
                headers_lower = {k.lower(): v for k, v in headers.items()}
                api_key = extract_api_key(headers_lower)
                if api_key:
                    source = "ctx_request"
        except (TokenExpiredError, TokenInvalidError) as e:
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message=str(e))
            ) from e
        except Exception:
            pass

    if api_key:
        logger.debug(
            "require_api_key_result",
            extra={"has_key": True, "source": source},
        )

    if not api_key:
        raise McpError(
            ErrorData(
                code=INVALID_PARAMS,
                message=(
                    "No API key provided. "
                    "Pass X-API-Key header or "
                    "Authorization: Bearer <token>. "
                    "Get a free key at "
                    "asterwise.com/dashboard"
                ),
            )
        )

    return api_key


def format_tool_result(
    data: dict[str, Any],
    response_format: ResponseFormat,
    to_markdown: Callable[[dict[str, Any]], str],
) -> str:
    """Return JSON or markdown per tool contract (leak keys scrubbed)."""
    cleaned = scrub_tool_payload(data)
    if not isinstance(cleaned, dict):
        cleaned = {"data": cleaned}
    if response_format == ResponseFormat.JSON:
        return json.dumps(cleaned, indent=2, default=str)
    return to_markdown(cleaned)


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
