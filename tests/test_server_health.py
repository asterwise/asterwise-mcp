"""/health endpoint."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_upstream_200(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTERWISE_API_BASE_URL", "https://api.example.com")

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def get(self, url: str):
            r = MagicMock()
            r.status_code = 200
            return r

    with patch("server.httpx.AsyncClient", FakeClient):
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r = await ac.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["upstream"]["reachable"] is True


@pytest.mark.asyncio
async def test_health_upstream_not_200(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTERWISE_API_BASE_URL", "https://api.example.com")

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def get(self, url: str):
            r = MagicMock()
            r.status_code = 503
            return r

    with patch("server.httpx.AsyncClient", FakeClient):
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r = await ac.get("/health")
    assert r.status_code == 503
    assert r.json()["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_no_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASTERWISE_API_BASE_URL", raising=False)

    with patch("server.httpx.AsyncClient", MagicMock()):
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r = await ac.get("/health")
    assert r.status_code == 503
    assert "not set" in (r.json().get("upstream") or {}).get("error", "")
