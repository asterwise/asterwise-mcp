"""
Only failures on our side reach Sentry, once each.

Sentry's MCP integration (auto-enabled in sentry-sdk) captures every
exception a tool call raises, including a caller's bad input
(ASTERWISE-API-2A: birth time '24:30'; ASTERWISE-API-2B: an invalid
timezone the API rejected with 422). Tool errors are reported explicitly by
runtime.tool_guard -> observability.capture_tool_failure: API 5xx and
crashes, never 4xx or validation errors.
"""

from __future__ import annotations

from typing import Any

import pytest
import sentry_sdk
from fastmcp import Client
from mcp.shared.exceptions import McpError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS

import client as client_mod
import observability
import runtime
from context import set_request_api_key
from errors import AsterwiseAPIError, map_http_status_to_message
from server import mcp
from tests.test_observability import live_sentry  # noqa: F401  (fixture)

TOOL = "asterwise_get_lal_kitab_remedies"
GOOD_BIRTH = {
    "date": "1985-11-12",
    "time": "06:45",
    "lat": 19.076,
    "lon": 72.8777,
    "timezone": "Asia/Kolkata",
}


class FailingUpstream:
    def __init__(self, exc: BaseException) -> None:
        self.exc = exc

    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def get(self, *a: Any, **kw: Any):
        raise self.exc

    async def post(self, *a: Any, **kw: Any):
        raise self.exc


async def _call(args: dict[str, Any], upstream: Any) -> Any:
    client_mod._client_singleton = upstream
    set_request_api_key("aw_test_key_0123456789")
    try:
        async with Client(mcp) as c:
            return await c.call_tool(TOOL, args, raise_on_error=False)
    finally:
        set_request_api_key(None)
        client_mod._client_singleton = None


def _api_error(status: int) -> AsterwiseAPIError:
    return AsterwiseAPIError(
        map_http_status_to_message(status, "timezone must be a valid IANA timezone"),
        status_code=status,
        api_request_id="rid-test-12345678",
    )


@pytest.mark.asyncio
async def test_bad_input_rejected_by_tool_schema_is_not_reported(live_sentry):  # noqa: F811
    result = await _call({"birth": {**GOOD_BIRTH, "time": "24:30"}}, FailingUpstream(AssertionError("not called")))
    sentry_sdk.flush()
    assert result.is_error
    assert live_sentry.events == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403, 404, 422, 429])
async def test_api_client_errors_are_not_reported(live_sentry, status):  # noqa: F811
    result = await _call({"birth": GOOD_BIRTH}, FailingUpstream(_api_error(status)))
    sentry_sdk.flush()
    assert result.is_error
    assert live_sentry.events == []


@pytest.mark.asyncio
async def test_api_server_error_is_reported_once(live_sentry):  # noqa: F811
    result = await _call({"birth": GOOD_BIRTH}, FailingUpstream(_api_error(503)))
    sentry_sdk.flush()
    assert result.is_error
    assert len(live_sentry.events) == 1
    assert live_sentry.events[0]["tags"]["tool"] == TOOL
    assert live_sentry.events[0]["tags"]["upstream_status"] == "503"


@pytest.mark.asyncio
async def test_crash_is_reported_once(live_sentry):  # noqa: F811
    result = await _call({"birth": GOOD_BIRTH}, FailingUpstream(RuntimeError("engine blew up")))
    sentry_sdk.flush()
    assert result.is_error
    assert len(live_sentry.events) == 1
    assert live_sentry.events[0]["tags"]["failure"] == "crash"


@pytest.mark.asyncio
@pytest.mark.parametrize(("status", "code"), [
    (400, INVALID_PARAMS),
    (422, INVALID_PARAMS),
    (401, INTERNAL_ERROR),
    (429, INTERNAL_ERROR),
    (503, INTERNAL_ERROR),
])
async def test_api_input_rejection_is_an_invalid_params_error(status, code):
    with pytest.raises(McpError) as caught:
        async with runtime.tool_guard(TOOL):
            raise _api_error(status)
    assert caught.value.error.code == code



def _chain(outer: BaseException, cause: BaseException) -> BaseException:
    try:
        try:
            raise cause
        except BaseException as inner:
            raise outer from inner
    except BaseException as exc:
        return exc


def _sent(exc: BaseException) -> bool:
    event = {"exception": {"values": [{"type": type(exc).__name__}]}}
    return observability._before_send(event, {"exc_info": (type(exc), exc, exc.__traceback__)}) is not None


def test_filter_drops_errors_already_answered_to_the_caller():
    from fastmcp.exceptions import ToolError
    from fastmcp.exceptions import ValidationError as FastMCPValidationError
    from mcp.types import ErrorData

    mcp_error = McpError(ErrorData(code=INVALID_PARAMS, message="bad timezone"))
    # ASTERWISE-API-2B: fastmcp wraps the guard's McpError in ToolError.
    assert not _sent(_chain(ToolError("Error calling tool"), mcp_error))
    assert not _sent(mcp_error)
    # ASTERWISE-API-2A: tool-schema validation of the arguments.
    assert not _sent(FastMCPValidationError("time must be HH:MM"))


def test_filter_keeps_crashes_that_escaped_the_guard():
    from fastmcp.exceptions import ToolError

    assert _sent(_chain(ToolError("Error calling tool"), RuntimeError("boom")))
    assert _sent(RuntimeError("boom"))
    assert _sent(_api_error(503))


def test_filter_keeps_events_without_an_exception():
    assert observability._before_send({"message": "hello"}, {}) is not None
    assert observability._before_send({"message": "hello"}, None) is not None
