"""OAuth /oauth/token endpoint behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_upstream_get(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    import server as srv

    mock_c = MagicMock()
    mock_c.get = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(srv, "get_client", lambda: mock_c)
    return mock_c


@pytest.mark.asyncio
class TestOAuthEndpoint:
    async def test_missing_body_returns_400(
        self,
        mock_upstream_get: MagicMock,
    ) -> None:
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/oauth/token",
                content="not json",
                headers={"Content-Type": "application/json"},
            )
        assert r.status_code == 400
        assert r.json()["error"] == "invalid_request"

    async def test_array_body_returns_400(
        self,
        mock_upstream_get: MagicMock,
    ) -> None:
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post("/oauth/token", json=["not", "an", "object"])
        assert r.status_code == 400

    async def test_unsupported_grant_type_returns_400(
        self,
        mock_upstream_get: MagicMock,
    ) -> None:
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/oauth/token",
                json={
                    "grant_type": "implicit",
                    "client_id": "key",
                    "client_secret": "key",
                },
            )
        assert r.status_code == 400
        assert "unsupported_grant_type" in r.json()["error"]

    async def test_authorization_code_missing_fields_returns_400(
        self,
        mock_upstream_get: MagicMock,
    ) -> None:
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "client_id": "key",
                    "client_secret": "key",
                },
            )
        assert r.status_code == 400
        assert r.json()["error"] == "invalid_request"

    async def test_mismatched_credentials_returns_401(
        self,
        mock_upstream_get: MagicMock,
    ) -> None:
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/oauth/token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": "key-a",
                    "client_secret": "key-b",
                },
            )
        assert r.status_code == 401
        assert "invalid_client" in r.json()["error"]

    async def test_missing_credentials_returns_401(
        self,
        mock_upstream_get: MagicMock,
    ) -> None:
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/oauth/token",
                json={"grant_type": "client_credentials"},
            )
        assert r.status_code == 401

    async def test_client_credentials_success_returns_token(
        self,
        mock_upstream_get: MagicMock,
    ) -> None:
        from server import app

        api_key = "valid-asterwise-api-key-for-oauth-test-12345"
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/oauth/token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": api_key,
                    "client_secret": api_key,
                },
            )
        assert r.status_code == 200
        body = r.json()
        assert body["token_type"] == "bearer"
        assert body["scope"] == "asterwise:read"
        assert len(body["access_token"].split(".")) == 3
        mock_upstream_get.get.assert_called()
