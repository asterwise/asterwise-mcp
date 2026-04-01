"""require_api_key via FastMCP Context."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from mcp.shared.exceptions import McpError
from mcp.types import INVALID_PARAMS

from runtime import require_api_key


@pytest.mark.asyncio
async def test_require_api_key_reads_x_api_key_from_request() -> None:
    ctx = MagicMock()
    req = MagicMock()
    req.headers = {"x-api-key": "direct-key-xyz"}
    rc = MagicMock()
    rc.request = req
    ctx.request_context = rc

    assert await require_api_key(ctx) == "direct-key-xyz"


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
async def test_require_api_key_no_request_context() -> None:
    ctx = MagicMock()
    ctx.request_context = None

    with pytest.raises(McpError) as exc:
        await require_api_key(ctx)
    assert exc.value.error.code == INVALID_PARAMS
