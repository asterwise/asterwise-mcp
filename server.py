"""Asterwise MCP server — streamable HTTP, OAuth, health, structured logs."""

from __future__ import annotations

import hmac
import json
import logging
import os
import time
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from context import set_request_api_key

load_dotenv()

from logging_config import configure_logging

configure_logging()

from auth import TOKEN_TTL, _token_cache, create_token
from client import get_client
from errors import AsterwiseAPIError
from tools import dasha, horoscope, matchmaking, natal, numerology, panchanga, reports, yoga_dosha

logger = logging.getLogger("asterwise_mcp.server")


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Resolve Bearer / X-API-Key from HTTP headers into a ContextVar for tool handlers."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        logger.debug(
            "middleware_auth_enter",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )
        api_key: str | None = None
        auth_header = request.headers.get("authorization", "")
        bearer_present = False
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            bearer_present = bool(token)
            if token:
                try:
                    from auth import decode_token

                    api_key = decode_token(token)
                except Exception:
                    pass

        xkey_present = bool(request.headers.get("x-api-key", "").strip())
        if not api_key:
            api_key = request.headers.get("x-api-key", "").strip() or None

        # ContextVar: tools read via get_request_api_key() (same async context as MCP handler).
        set_request_api_key(api_key)
        # request.state: available to any code with access to the Starlette Request.
        request.state.api_key = api_key

        logger.debug(
            "middleware_auth",
            extra={
                "path": request.url.path,
                "has_api_key": api_key is not None,
                "method": (
                    "bearer_jwt"
                    if bearer_present
                    else "x_api_key"
                    if xkey_present
                    else "none"
                ),
            },
        )
        try:
            response = await call_next(request)
            return response
        finally:
            set_request_api_key(None)
            request.state.api_key = None


API_KEY_MIDDLEWARE: list[Middleware] = [Middleware(APIKeyMiddleware)]

# OAuth token endpoint: max 10 requests per minute per IP (in-memory)
_oauth_attempts: dict[str, list[float]] = {}
_OAUTH_MAX = 10
_OAUTH_WINDOW_SEC = 60.0


def _oauth_rate_allow(client_ip: str) -> bool:
    now = time.time()
    times = _oauth_attempts.setdefault(client_ip, [])
    times[:] = [t for t in times if now - t < _OAUTH_WINDOW_SEC]
    if len(times) >= _OAUTH_MAX:
        return False
    times.append(now)
    return True


def _api_base() -> str:
    return os.getenv("ASTERWISE_API_BASE_URL", "").rstrip("/")


def _internal_bearer_headers() -> dict[str, str] | None:
    token = os.getenv("ASTERWISE_INTERNAL_TOKEN", "").strip()
    if not token:
        return None
    return {"Authorization": f"Bearer {token}"}


def _redirect_uri_allowed(uri: str) -> bool:
    p = urlparse(uri.strip())
    if not p.scheme or not p.netloc:
        return False
    if p.scheme == "https":
        return True
    if p.scheme != "http":
        return False
    host = (p.hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    return host.endswith(".localhost")


def _response_body_bytes(resp: Response) -> bytes:
    """Read body from Starlette ``Response`` (``body``) or httpx-like (``content``)."""
    raw = getattr(resp, "body", None)
    if raw is None:
        raw = getattr(resp, "content", b"")
    if isinstance(raw, memoryview):
        return raw.tobytes()
    if isinstance(raw, bytes):
        return raw
    return bytes(raw)


async def _forward_upstream_json(
    path: str,
    body: dict,
    *,
    extra_headers: dict[str, str] | None = None,
) -> Response:
    base = _api_base()
    if not base:
        return JSONResponse(
            {
                "error": "server_error",
                "error_description": "ASTERWISE_API_BASE_URL is not configured",
            },
            status_code=500,
        )
    url = f"{base}{path}"
    headers = dict(extra_headers or {})
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, json=body, headers=headers)
        ct = r.headers.get("content-type") or "application/json"
        media = ct.split(";")[0].strip()
        return Response(content=r.content, status_code=r.status_code, media_type=media)
    except httpx.RequestError as e:
        logger.warning(
            "upstream_oauth_unreachable",
            extra={"url": url, "error": str(e)},
        )
        return JSONResponse(
            {
                "error": "temporarily_unavailable",
                "error_description": "Upstream OAuth service unreachable",
            },
            status_code=503,
        )


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    _ = server
    client = get_client()
    await client.open()
    try:
        yield {}
    finally:
        await client.close()


mcp = FastMCP(
    "asterwise_mcp",
    instructions="""
You are connected to the Asterwise Vedic Astrology API.

This MCP server gives you access to classical Jyotish (Vedic astrology) calculations
derived from the source texts — BPHS, Phaladeepika, and Saravali — with chapter and
verse citations in every response.

Key capabilities:
- Natal charts with planet positions, nakshatras, flags
- 5-level Vimshottari Dasha (most APIs return only 2)
- Classical matchmaking with hard vetoes (not scores)
- Fresh horoscopes computed from live planetary positions
- 12 dosha analysis, 25+ yoga detection
- Numerology (Pythagorean, Chaldean, Lo Shu)
- Panchanga, Muhurta, Choghadiya timing
- KP, Lal Kitab, Char Dasha, Yogini systems

Always use lahiri ayanamsa unless the user specifies KP (use kp ayanamsa) or explicitly
requests Western/tropical.

For matchmaking: always check Rajju and Vedha as vetoes first. A failed veto means the
match should not proceed regardless of Guna score — this is Parashara's explicit
instruction, not a soft recommendation.

Birth data required for most tools:
- date: YYYY-MM-DD
- time: HH:MM (24-hour, local time at birth location)
- lat: latitude (decimal degrees)
- lon: longitude (decimal degrees)

If the user provides a city name instead of coordinates, ask for the coordinates or
use a geocoding service to look them up. The API requires decimal degree coordinates.
""",
    lifespan=lifespan,
)


def _register_tools() -> None:
    natal.register(mcp)
    dasha.register(mcp)
    matchmaking.register(mcp)
    panchanga.register(mcp)
    yoga_dosha.register(mcp)
    numerology.register(mcp)
    horoscope.register(mcp)
    reports.register(mcp)


_register_tools()


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    """Health with upstream probe and token cache size."""
    _ = request
    start = time.perf_counter()
    upstream_ok = False
    upstream_error: str | None = None
    base = os.getenv("ASTERWISE_API_BASE_URL", "").rstrip("/")

    if base:
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.get(f"{base}/health")
                upstream_ok = r.status_code == 200
        except Exception as e:
            upstream_error = str(e)
    else:
        upstream_error = "ASTERWISE_API_BASE_URL not set"

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    body = {
        "status": "ok" if upstream_ok else "degraded",
        "version": "1.0.0",
        "upstream": {"reachable": upstream_ok, "error": upstream_error},
        "latency_ms": elapsed,
        "token_cache_size": len(_token_cache),
    }
    return JSONResponse(body, status_code=200 if upstream_ok else 503)


@mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
async def oauth_metadata(request: Request) -> Response:
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    _ = request
    return JSONResponse(
        {
            "issuer": "https://mcp.asterwise.com",
            "authorization_endpoint": "https://asterwise.com/oauth/authorize",
            "token_endpoint": "https://mcp.asterwise.com/oauth/token",
            "registration_endpoint": "https://mcp.asterwise.com/register",
            "token_endpoint_auth_methods_supported": [
                "client_secret_post",
            ],
            "grant_types_supported": [
                "authorization_code",
                "client_credentials",
                "refresh_token",
            ],
            "response_types_supported": ["code"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": [
                "asterwise:read",
            ],
            "revocation_endpoint": "https://mcp.asterwise.com/oauth/revoke",
        }
    )


@mcp.custom_route("/.well-known/openid-configuration", methods=["GET"])
async def openid_metadata(request: Request) -> Response:
    """OpenID Connect Discovery (for broad compatibility)."""
    _ = request
    return JSONResponse(
        {
            "issuer": "https://mcp.asterwise.com",
            "authorization_endpoint": "https://asterwise.com/oauth/authorize",
            "token_endpoint": "https://mcp.asterwise.com/oauth/token",
            "registration_endpoint": "https://mcp.asterwise.com/register",
            "token_endpoint_auth_methods_supported": [
                "client_secret_post",
            ],
            "grant_types_supported": [
                "authorization_code",
                "client_credentials",
                "refresh_token",
            ],
            "response_types_supported": ["code"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": [
                "asterwise:read",
            ],
            "revocation_endpoint": "https://mcp.asterwise.com/oauth/revoke",
        }
    )


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def oauth_protected_resource_metadata(request: Request) -> Response:
    """OAuth 2.0 Protected Resource Metadata (MCP authorization, 2025-06-18)."""
    _ = request
    return JSONResponse(
        {
            "resource": "https://mcp.asterwise.com",
            "authorization_servers": ["https://mcp.asterwise.com"],
            "scopes_supported": ["asterwise:read"],
            "bearer_methods_supported": ["header"],
        }
    )


@mcp.custom_route("/register", methods=["POST"])
async def oauth_dynamic_client_register(request: Request) -> Response:
    """RFC 7591-style dynamic client registration (proxied to asterwise-api)."""
    client_ip = request.client.host if request.client else "unknown"
    if not _oauth_rate_allow(client_ip):
        return JSONResponse(
            {
                "error": "too_many_requests",
                "error_description": "Rate limit: max 10 token requests per minute per IP.",
            },
            status_code=429,
        )

    try:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "Request body must be valid JSON",
                },
                status_code=400,
            )

        if not isinstance(body, dict):
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "Request body must be a JSON object",
                },
                status_code=400,
            )

        redirect_uris = body.get("redirect_uris")
        if not isinstance(redirect_uris, list) or len(redirect_uris) == 0:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "redirect_uris must be a non-empty array",
                },
                status_code=400,
            )
        if not all(isinstance(u, str) and u.strip() for u in redirect_uris):
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "Each redirect_uris entry must be a non-empty string",
                },
                status_code=400,
            )
        for u in redirect_uris:
            if not _redirect_uri_allowed(u):
                return JSONResponse(
                    {
                        "error": "invalid_request",
                        "error_description": (
                            "All redirect_uris must use https, or http only for "
                            "localhost development"
                        ),
                    },
                    status_code=400,
                )

        grant_types = body.get("grant_types")
        if grant_types is None:
            grant_types = ["authorization_code"]
        elif not isinstance(grant_types, list) or not all(
            isinstance(g, str) for g in grant_types
        ):
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "grant_types must be a list of strings",
                },
                status_code=400,
            )

        scope = body.get("scope")
        if scope is None:
            scope = "asterwise:read"
        elif not isinstance(scope, str):
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "scope must be a string",
                },
                status_code=400,
            )

        client_name = body.get("client_name")
        if client_name is not None and not isinstance(client_name, str):
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "client_name must be a string",
                },
                status_code=400,
            )

        hdrs = _internal_bearer_headers()
        if hdrs is None:
            return JSONResponse(
                {
                    "error": "service_unavailable",
                    "error_description": "Client registration is not configured",
                },
                status_code=503,
            )

        upstream_body = {
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "grant_types": grant_types,
            "scope": scope,
        }
        resp = await _forward_upstream_json(
            "/v1/oauth/register",
            upstream_body,
            extra_headers=hdrs,
        )
        if resp.status_code == 503:
            return resp
        if resp.status_code >= 500:
            return JSONResponse(
                {
                    "error": "server_error",
                    "error_description": "Registration failed",
                },
                status_code=500,
            )
        if resp.status_code not in (200, 201):
            raw = _response_body_bytes(resp)
            try:
                err_body = json.loads(raw.decode("utf-8"))
            except Exception:
                err_body = {
                    "error": "invalid_request",
                    "error_description": raw.decode("utf-8", errors="replace"),
                }
            return JSONResponse(err_body, status_code=resp.status_code)

        try:
            data = json.loads(_response_body_bytes(resp).decode("utf-8"))
        except Exception:
            logger.exception("register_upstream_bad_json")
            return JSONResponse(
                {
                    "error": "server_error",
                    "error_description": "Invalid upstream response",
                },
                status_code=500,
            )

        if "client_id" not in data or "client_secret" not in data:
            return JSONResponse(
                {
                    "error": "server_error",
                    "error_description": "Invalid upstream registration response",
                },
                status_code=500,
            )

        cid = data["client_id"]
        csec = data["client_secret"]
        issued = int(time.time())
        return JSONResponse(
            {
                "client_id": cid,
                "client_secret": csec,
                "client_id_issued_at": issued,
                "client_secret_expires_at": 0,
                "redirect_uris": redirect_uris,
                "grant_types": grant_types,
                "scope": scope,
                "token_endpoint_auth_method": "client_secret_post",
            },
            status_code=201,
        )
    except Exception:
        logger.exception("register_unhandled")
        return JSONResponse(
            {
                "error": "server_error",
                "error_description": "Registration failed",
            },
            status_code=500,
        )


@mcp.custom_route("/oauth/revoke", methods=["POST"])
async def oauth_revoke(request: Request) -> Response:
    """RFC 7009 token revocation (proxied); always 200 for the client."""
    body: dict[str, Any] = {}
    try:
        raw = await request.json()
        if isinstance(raw, dict):
            body = raw
    except Exception:
        try:
            form = await request.form()
            body = {str(k): v for k, v in form.multi_items()}
        except Exception:
            body = {}

    base = _api_base()
    if base:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(f"{base}/v1/oauth/revoke", json=body)
        except httpx.RequestError:
            pass
    return Response(status_code=200)


@mcp.custom_route("/oauth/token", methods=["POST"])
async def oauth_token(request: Request) -> Response:
    """OAuth token: client_credentials (local JWT) or proxy auth_code / refresh to API."""
    client_ip = request.client.host if request.client else "unknown"
    if not _oauth_rate_allow(client_ip):
        return JSONResponse(
            {
                "error": "too_many_requests",
                "error_description": "Rate limit: max 10 token requests per minute per IP.",
            },
            status_code=429,
        )

    try:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "Request body must be valid JSON",
                },
                status_code=400,
            )

        if not isinstance(body, dict):
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "Request body must be a JSON object",
                },
                status_code=400,
            )

        grant_type = body.get("grant_type", "")

        if grant_type == "authorization_code":
            required = (
                "code",
                "redirect_uri",
                "client_id",
                "client_secret",
                "code_verifier",
            )
            for k in required:
                v = body.get(k)
                if v is None or (isinstance(v, str) and not str(v).strip()):
                    return JSONResponse(
                        {
                            "error": "invalid_request",
                            "error_description": (
                                f"Missing or empty required field: {k}"
                            ),
                        },
                        status_code=400,
                    )
            return await _forward_upstream_json("/v1/oauth/token", dict(body))

        if grant_type == "refresh_token":
            for k in ("refresh_token", "client_id", "client_secret"):
                v = body.get(k)
                if v is None or (isinstance(v, str) and not str(v).strip()):
                    return JSONResponse(
                        {
                            "error": "invalid_request",
                            "error_description": (
                                f"Missing or empty required field: {k}"
                            ),
                        },
                        status_code=400,
                    )
            return await _forward_upstream_json("/v1/oauth/token", dict(body))

        if grant_type != "client_credentials":
            return JSONResponse(
                {
                    "error": "unsupported_grant_type",
                    "error_description": f"Unsupported grant_type: {grant_type!r}",
                },
                status_code=400,
            )

        client_id = str(body.get("client_id", "")).strip()
        client_secret = str(body.get("client_secret", "")).strip()

        if not client_id or not client_secret:
            return JSONResponse(
                {
                    "error": "invalid_client",
                    "error_description": (
                        "Both client_id and client_secret are required. "
                        "They must equal your Asterwise API key."
                    ),
                },
                status_code=401,
            )

        try:
            cid_b = client_id.encode("utf-8")
            csec_b = client_secret.encode("utf-8")
            if len(cid_b) != len(csec_b) or not hmac.compare_digest(cid_b, csec_b):
                return JSONResponse(
                    {
                        "error": "invalid_client",
                        "error_description": (
                            "client_id and client_secret must match and must equal "
                            "your Asterwise API key."
                        ),
                    },
                    status_code=401,
                )
        except Exception:
            return JSONResponse(
                {"error": "invalid_client", "error_description": "Invalid credentials."},
                status_code=401,
            )

        try:
            await get_client().get(
                "/v1/numerology/meaning/1",
                client_id,
                timeout=10.0,
            )
        except AsterwiseAPIError as e:
            return JSONResponse(
                {"error": "invalid_client", "error_description": str(e)},
                status_code=401,
            )
        except httpx.TimeoutException:
            return JSONResponse(
                {
                    "error": "temporarily_unavailable",
                    "error_description": (
                        "Upstream validation timed out. Try again in a moment. "
                        "Check status.asterwise.com"
                    ),
                },
                status_code=503,
            )
        except Exception as e:
            logger.error(
                "oauth_upstream_error",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            return JSONResponse(
                {
                    "error": "server_error",
                    "error_description": (
                        "Token issuance failed. Check status.asterwise.com"
                    ),
                },
                status_code=500,
            )

        try:
            token = create_token(client_id)
        except RuntimeError as e:
            return JSONResponse(
                {"error": "server_error", "error_description": str(e)},
                status_code=503,
            )

        return JSONResponse(
            {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": TOKEN_TTL,
                "scope": "asterwise:read",
            }
        )
    except Exception:
        logger.exception("oauth_token_unhandled")
        return JSONResponse(
            {
                "error": "server_error",
                "error_description": "Token endpoint failed. Check status.asterwise.com",
            },
            status_code=500,
        )


# Public ASGI app for tests and mounting
app = mcp.http_app(transport="streamable-http", middleware=API_KEY_MIDDLEWARE)


if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8000"))
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        middleware=API_KEY_MIDDLEWARE,
    )
