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
    # Liveness stays 200 so the platform health check does not restart this
    # service when the upstream API blips; degradation is reported in the body.
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    assert body["liveness"] == "ok"
    assert body["upstream"]["reachable"] is False
    assert "HTTP 503" in body["upstream"]["error"]


@pytest.mark.asyncio
async def test_health_no_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASTERWISE_API_BASE_URL", raising=False)

    with patch("server.httpx.AsyncClient", MagicMock()):
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r = await ac.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "degraded"
    assert "not set" in (r.json().get("upstream") or {}).get("error", "")


@pytest.mark.asyncio
async def test_health_upstream_timeout_names_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """httpx timeouts stringify to '' — the body must still say what happened."""
    import httpx

    monkeypatch.setenv("ASTERWISE_API_BASE_URL", "https://api.example.com")

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def get(self, url: str):
            raise httpx.ReadTimeout("")

    with patch("server.httpx.AsyncClient", FakeClient):
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r = await ac.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    assert body["upstream"]["reachable"] is False
    assert body["upstream"]["error"] == "ReadTimeout"


@pytest.mark.asyncio
async def test_health_uses_pooled_client_when_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the lifespan has opened the shared client, the probe must reuse it."""
    monkeypatch.setenv("ASTERWISE_API_BASE_URL", "https://api.example.com")

    pooled = MagicMock()
    ok = MagicMock()
    ok.status_code = 200
    pooled.get = AsyncMock(return_value=ok)
    fake_singleton = MagicMock()
    fake_singleton._http = pooled

    with patch("server.get_client", return_value=fake_singleton), patch(
        "server.httpx.AsyncClient", side_effect=AssertionError("must not create a new client")
    ):
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r = await ac.get("/health")
    assert r.status_code == 200
    assert r.json()["upstream"]["reachable"] is True
    pooled.get.assert_awaited_once()
    assert pooled.get.await_args.args[0] == "/health"
