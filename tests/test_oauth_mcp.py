"""OAuth metadata, DCR, token proxy, revoke (MCP + PKCE)."""

from __future__ import annotations

import json
import os
import time
from unittest.mock import patch

import jwt as pyjwt
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.responses import JSONResponse, Response

from auth import ISSUER, TOKEN_TTL, _fernet_from_secret, _hash_key, create_token, decode_token


@pytest.fixture(autouse=True)
def _oauth_rate_off(monkeypatch: pytest.MonkeyPatch) -> None:
    import server as srv

    monkeypatch.setattr(srv, "_oauth_rate_allow", lambda _ip: True)


@pytest.mark.asyncio
async def test_unauthenticated_mcp_returns_401_with_www_authenticate() -> None:
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/mcp")
    assert r.status_code == 401
    assert "www-authenticate" in {k.lower() for k in r.headers.keys()}
    wwa = r.headers.get("www-authenticate") or r.headers.get("WWW-Authenticate", "")
    assert "resource_metadata" in wwa
    assert "Asterwise MCP" in wwa
    body = r.json()
    assert body["error"] == "unauthorized"
    assert "asterwise.com/dashboard" in body["error_description"]


@pytest.mark.asyncio
async def test_options_request_bypasses_auth_required() -> None:
    """OPTIONS must not receive middleware 401 (CORS preflight). Use /health so the
    request reaches the app without FastMCP /mcp lifespan requirements in tests."""
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.request("OPTIONS", "/health")
    assert r.status_code != 401


@pytest.mark.asyncio
async def test_register_empty_redirect_uris_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_TOKEN", "internal-test-token")
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/oauth/register", json={"redirect_uris": []})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_register_malformed_json_returns_400() -> None:
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/oauth/register",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_request"


@pytest.mark.asyncio
async def test_register_missing_internal_token_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTERNAL_API_TOKEN", raising=False)
    monkeypatch.setenv("ASTERWISE_API_BASE_URL", "https://api.example.com")
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/oauth/register",
            json={"redirect_uris": ["https://app/cb"]},
        )
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_register_upstream_unreachable_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_TOKEN", "internal-test-token")
    monkeypatch.setenv("ASTERWISE_API_BASE_URL", "https://api.example.com")

    async def fake_forward(
        path: str,
        body: dict,
        *,
        extra_headers: dict | None = None,
    ) -> JSONResponse:
        return JSONResponse(
            {"error": "temporarily_unavailable"},
            status_code=503,
        )

    import server as srv

    monkeypatch.setattr(srv, "_forward_upstream_json", fake_forward)
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/oauth/register",
            json={"redirect_uris": ["https://app/cb"]},
        )
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_register_endpoint_validates_https(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_TOKEN", "internal-test-token")
    monkeypatch.setenv("ASTERWISE_API_BASE_URL", "https://api.example.com")
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/oauth/register",
            json={
                "redirect_uris": ["http://evil.com/cb"],
            },
        )
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_request"


@pytest.mark.asyncio
async def test_register_endpoint_accepts_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_API_TOKEN", "internal-test-token")
    monkeypatch.setenv("ASTERWISE_API_BASE_URL", "https://api.example.com")

    async def fake_forward(
        path: str,
        body: dict,
        *,
        extra_headers: dict | None = None,
    ) -> Response:
        assert path == "/v1/oauth/register"
        assert body["redirect_uris"] == ["http://localhost:3000/cb"]
        return Response(
            content=json.dumps(
                {"client_id": "cid-1", "client_secret": "sec-1"}
            ).encode(),
            status_code=201,
            media_type="application/json",
        )

    import server as srv

    monkeypatch.setattr(srv, "_forward_upstream_json", fake_forward)

    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/oauth/register",
            json={"redirect_uris": ["http://localhost:3000/cb"]},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["client_id"] == "cid-1"
    assert data["token_endpoint_auth_method"] == "client_secret_post"


@pytest.mark.asyncio
async def test_openid_configuration_matches_as_metadata() -> None:
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/.well-known/openid-configuration")
    assert r.status_code == 200
    meta = r.json()
    assert meta["authorization_endpoint"] == "https://mcp.asterwise.com/authorize"
    assert meta["registration_endpoint"] == "https://mcp.asterwise.com/oauth/register"
    assert meta["code_challenge_methods_supported"] == ["S256"]


@pytest.mark.asyncio
async def test_well_known_includes_authorization_endpoint() -> None:
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/.well-known/oauth-authorization-server")
    assert r.status_code == 200
    meta = r.json()
    assert meta["authorization_endpoint"] == "https://mcp.asterwise.com/authorize"


@pytest.mark.asyncio
async def test_oauth_authorize_proxy_redirects_to_frontend() -> None:
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=False
    ) as ac:
        r = await ac.get("/oauth/authorize")
    assert r.status_code == 302
    assert r.headers.get("location") == "https://asterwise.com/oauth/authorize"


@pytest.mark.asyncio
async def test_oauth_authorize_proxy_preserves_query_string() -> None:
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=False
    ) as ac:
        r = await ac.get("/oauth/authorize?client_id=cid&response_type=code")
    assert r.status_code == 302
    loc = r.headers.get("location") or ""
    assert loc.startswith("https://asterwise.com/oauth/authorize?")
    assert "client_id=cid" in loc


@pytest.mark.asyncio
async def test_well_known_includes_registration_endpoint() -> None:
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/.well-known/oauth-authorization-server")
    assert r.json()["registration_endpoint"] == "https://mcp.asterwise.com/oauth/register"


@pytest.mark.asyncio
async def test_well_known_includes_s256_pkce() -> None:
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/.well-known/oauth-authorization-server")
    assert r.json()["code_challenge_methods_supported"] == ["S256"]


@pytest.mark.asyncio
async def test_protected_resource_metadata_returns_200() -> None:
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/.well-known/oauth-protected-resource")
    assert r.status_code == 200
    body = r.json()
    assert body["resource"] == "https://mcp.asterwise.com"
    assert body["authorization_servers"] == ["https://mcp.asterwise.com"]


@pytest.mark.asyncio
async def test_token_refresh_missing_field_returns_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ASTERWISE_API_BASE_URL", "https://api.example.com")
    from server import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/oauth/token",
            json={
                "grant_type": "refresh_token",
                "refresh_token": "rt",
                "client_id": "c",
            },
        )
    assert r.status_code == 400
    assert "client_secret" in r.json()["error_description"]


@pytest.mark.asyncio
async def test_token_endpoint_forwards_refresh_token_grant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTERWISE_API_BASE_URL", "https://api.example.com")
    captured: list[dict] = []

    async def fake_forward(
        path: str,
        body: dict,
        *,
        extra_headers: dict | None = None,
    ) -> Response:
        captured.append(dict(body))
        return Response(
            content=b'{"access_token":"refreshed","token_type":"bearer"}',
            status_code=200,
            media_type="application/json",
        )

    import server as srv

    monkeypatch.setattr(srv, "_forward_upstream_json", fake_forward)
    from server import app

    transport = ASGITransport(app=app)
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": "rt",
        "client_id": "cid",
        "client_secret": "sec",
    }
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/oauth/token", json=payload)
    assert r.status_code == 200
    assert r.json()["access_token"] == "refreshed"
    assert captured[0] == payload


@pytest.mark.asyncio
async def test_token_endpoint_forwards_auth_code_grant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTERWISE_API_BASE_URL", "https://api.example.com")
    captured: list[tuple[str, dict]] = []

    async def fake_forward(
        path: str,
        body: dict,
        *,
        extra_headers: dict | None = None,
    ) -> Response:
        captured.append((path, dict(body)))
        return Response(
            content=b'{"access_token":"from-api","token_type":"bearer"}',
            status_code=200,
            media_type="application/json",
        )

    import server as srv

    monkeypatch.setattr(srv, "_forward_upstream_json", fake_forward)
    from server import app

    transport = ASGITransport(app=app)
    payload = {
        "grant_type": "authorization_code",
        "code": "abc",
        "redirect_uri": "https://app/cb",
        "client_id": "cid",
        "client_secret": "sec",
        "code_verifier": "ver",
    }
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/oauth/token", json=payload)
    assert r.status_code == 200
    assert r.json()["access_token"] == "from-api"
    assert captured[0][0] == "/v1/oauth/token"
    assert captured[0][1] == payload


@pytest.mark.asyncio
async def test_revoke_endpoint_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASTERWISE_API_BASE_URL", "https://api.example.com")

    class FakeClient:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *a: object) -> None:
            return None

        async def post(self, url: str, json: dict | None = None) -> object:
            self.last_url = url
            self.last_json = json
            r = type("R", (), {})()
            r.status_code = 200
            return r

    fake = FakeClient()
    with patch("server.httpx.AsyncClient", lambda *a, **k: fake):
        from server import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post(
                "/oauth/revoke",
                json={"token": "t", "client_id": "c", "client_secret": "s"},
            )
    assert r.status_code == 200
    assert getattr(fake, "last_url", "").endswith("/v1/oauth/revoke")


def test_decode_token_tries_both_secrets() -> None:
    jwt_s = "a" * 32
    oauth_s = "b" * 32
    with patch.dict(
        os.environ,
        {"JWT_SECRET": jwt_s, "MCP_OAUTH_SECRET": oauth_s},
        clear=False,
    ):
        api_key = "roundtrip-cc-key-12345"
        token_cc = create_token(api_key)
        assert decode_token(token_cc) == api_key

        f = _fernet_from_secret(oauth_s)
        enc = f.encrypt(b"oauth-key-xyz").decode("utf-8")
        payload = {
            "sub": _hash_key("oauth-key-xyz"),
            "key": enc,
            "iat": int(time.time()),
            "exp": int(time.time()) + TOKEN_TTL,
            "iss": ISSUER,
        }
        tok = pyjwt.encode(payload, oauth_s, algorithm="HS256")
        assert decode_token(tok) == "oauth-key-xyz"
