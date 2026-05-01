"""require_api_key: ContextVar (middleware) + optional ctx fallback."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS

from context import set_request_api_key
from runtime import require_api_key


@pytest.mark.asyncio
async def test_require_api_key_from_contextvar() -> None:
    set_request_api_key("direct-key-xyz")
    try:
        assert await require_api_key(None) == "direct-key-xyz"
    finally:
        set_request_api_key(None)


@pytest.mark.asyncio
async def test_contextvar_takes_precedence_over_ctx_fallback() -> None:
    set_request_api_key("from-middleware")
    ctx = MagicMock()
    rc = MagicMock()
    rc.request = MagicMock(headers={"x-api-key": "from-ctx"})
    ctx.request_context = rc
    try:
        assert await require_api_key(ctx) == "from-middleware"
    finally:
        set_request_api_key(None)


@pytest.mark.asyncio
async def test_require_api_key_reads_x_api_key_from_ctx_fallback() -> None:
    ctx = MagicMock()
    req = MagicMock()
    req.headers = {"x-api-key": "fallback-key"}
    rc = MagicMock()
    rc.request = req
    ctx.request_context = rc

    assert await require_api_key(ctx) == "fallback-key"


@pytest.mark.asyncio
async def test_require_api_key_missing_raises_invalid_params() -> None:
    ctx = MagicMock()
    rc = MagicMock()
    rc.request = MagicMock(headers={})
    ctx.request_context = rc

    with pytest.raises(McpError) as exc:
        await require_api_key(ctx)
    assert exc.value.error.code == INVALID_PARAMS


@pytest.mark.asyncio
async def test_require_api_key_no_request_context_and_no_contextvar() -> None:
    ctx = MagicMock()
    ctx.request_context = None

    with pytest.raises(McpError) as exc:
        await require_api_key(ctx)
    assert exc.value.error.code == INVALID_PARAMS
