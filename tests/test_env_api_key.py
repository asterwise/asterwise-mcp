"""Environment fallback for the API key (stdio deployments)."""

import pytest
from mcp.shared.exceptions import McpError

import runtime


@pytest.mark.asyncio
async def test_env_key_used_when_no_request_context(monkeypatch):
    monkeypatch.setenv("ASTERWISE_API_KEY", "aw_from_env")
    assert await runtime.require_api_key(None) == "aw_from_env"


@pytest.mark.asyncio
async def test_blank_env_key_is_ignored(monkeypatch):
    monkeypatch.setenv("ASTERWISE_API_KEY", "   ")
    with pytest.raises(McpError) as exc:
        await runtime.require_api_key(None)
    assert "ASTERWISE_API_KEY" in str(exc.value)


@pytest.mark.asyncio
async def test_request_key_wins_over_env(monkeypatch):
    from context import set_request_api_key

    monkeypatch.setenv("ASTERWISE_API_KEY", "aw_from_env")
    set_request_api_key("aw_from_request")
    try:
        assert await runtime.require_api_key(None) == "aw_from_request"
    finally:
        set_request_api_key(None)
