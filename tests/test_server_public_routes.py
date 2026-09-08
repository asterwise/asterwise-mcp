"""Unauthenticated crawler-facing routes: robots.txt and GET /."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


async def _client() -> AsyncClient:
    from server import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


@pytest.mark.asyncio
async def test_robots_txt_is_public_and_disallows_everything() -> None:
    async with await _client() as ac:
        r = await ac.get("/robots.txt")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert r.text == "User-agent: *\nDisallow: /\n"


@pytest.mark.asyncio
async def test_robots_txt_head() -> None:
    async with await _client() as ac:
        r = await ac.head("/robots.txt")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_root_get_redirects_to_product_page() -> None:
    async with await _client() as ac:
        r = await ac.get("/", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "https://asterwise.com/mcp/"


@pytest.mark.asyncio
async def test_root_head_still_answers_protocol_probe() -> None:
    async with await _client() as ac:
        r = await ac.head("/")
    assert r.status_code == 200
    assert r.headers.get("mcp-protocol-version")


@pytest.mark.asyncio
async def test_other_paths_remain_protected() -> None:
    async with await _client() as ac:
        r = await ac.get("/sitemap.xml")
    assert r.status_code == 401
