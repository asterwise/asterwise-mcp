"""Static MCP server card at /.well-known/mcp/server-card.json (Smithery scan bypass)."""

from __future__ import annotations

import pytest
from fastmcp import Client
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_server_card_is_public_and_matches_tools_list() -> None:
    from server import SERVER_VERSION, app, mcp

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/.well-known/mcp/server-card.json")
    assert r.status_code == 200, r.text
    assert "max-age" in r.headers.get("cache-control", "")
    card = r.json()

    assert card["serverInfo"] == {"name": mcp.name, "version": SERVER_VERSION}
    assert card["authentication"]["required"] is True
    assert "oauth2" in card["authentication"]["schemes"]
    assert card["authentication"]["apiKey"] == {"in": "header", "name": "x-api-key"}

    async with Client(mcp) as c:
        listed = {t.name: t for t in await c.list_tools()}
        prompts = {p.name for p in await c.list_prompts()}

    card_tools = {t["name"]: t for t in card["tools"]}
    assert set(card_tools) == set(listed)
    assert len(card_tools) >= 100
    for name, tool in card_tools.items():
        assert tool["description"] == listed[name].description
        assert tool["inputSchema"] == listed[name].inputSchema
    assert {p["name"] for p in card["prompts"]} == prompts
    assert card["resources"] == []


@pytest.mark.asyncio
async def test_server_card_second_request_served_from_cache() -> None:
    import server as srv
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = (await ac.get("/.well-known/mcp/server-card.json")).json()
        cached = srv._SERVER_CARD_CACHE
        assert cached is not None
        second = (await ac.get("/.well-known/mcp/server-card.json")).json()
    assert first == second
    assert srv._SERVER_CARD_CACHE is cached
