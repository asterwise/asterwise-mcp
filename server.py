"""Asterwise MCP server — streamable HTTP, OAuth, health, structured logs."""

from __future__ import annotations

import hmac
import logging
import os
import time
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
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            if token:
                try:
                    from auth import decode_token

                    api_key = decode_token(token)
                except Exception:
                    pass

        if not api_key:
            api_key = request.headers.get("x-api-key", "").strip() or None

        set_request_api_key(api_key)
        logger.debug(
            "middleware_auth",
            extra={
                "path": request.url.path,
                "has_api_key": api_key is not None,
                "method": request.method,
            },
        )
        try:
            response = await call_next(request)
            return response
        finally:
            set_request_api_key(None)


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
            "token_endpoint": "https://mcp.asterwise.com/oauth/token",
            "token_endpoint_auth_methods_supported": [
                "client_secret_post",
            ],
            "grant_types_supported": [
                "client_credentials",
            ],
            "response_types_supported": [
                "token",
            ],
            "scopes_supported": [
                "asterwise:read",
            ],
        }
    )


@mcp.custom_route("/.well-known/openid-configuration", methods=["GET"])
async def openid_metadata(request: Request) -> Response:
    """OpenID Connect Discovery (for broad compatibility)."""
    _ = request
    return JSONResponse(
        {
            "issuer": "https://mcp.asterwise.com",
            "token_endpoint": "https://mcp.asterwise.com/oauth/token",
            "token_endpoint_auth_methods_supported": [
                "client_secret_post",
            ],
            "grant_types_supported": [
                "client_credentials",
            ],
            "scopes_supported": [
                "asterwise:read",
            ],
        }
    )


@mcp.custom_route("/oauth/token", methods=["POST"])
async def oauth_token(request: Request) -> Response:
    """OAuth 2.1 client_credentials (API key as both id and secret)."""
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
        if grant_type != "client_credentials":
            return JSONResponse(
                {
                    "error": "unsupported_grant_type",
                    "error_description": (
                        f"Only 'client_credentials' is supported. Got: {grant_type!r}"
                    ),
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
