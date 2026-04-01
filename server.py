"""Asterwise MCP server — streamable HTTP transport, tools, OAuth token, health."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

load_dotenv()

from auth import create_token
from client import get_client
from errors import AsterwiseAPIError, AuthError
from tools import dasha, horoscope, matchmaking, natal, numerology, panchanga, reports, yoga_dosha


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Open the shared httpx client for the process lifetime."""
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


async def _validate_api_key_with_asterwise(api_key: str) -> None:
    """Lightweight authenticated call to prove the key works."""
    await get_client().get("/v1/numerology/meaning/1", api_key)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> Response:
    return JSONResponse({"status": "ok", "version": "1.0.0"})


@mcp.custom_route("/oauth/token", methods=["POST"])
async def oauth_token(request: Request) -> Response:
    """OAuth 2.1-style client_credentials using the API key as both id and secret."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {
                "error": "invalid_request",
                "error_description": "Send JSON: grant_type, client_id, client_secret (your API key).",
            },
            status_code=400,
        )

    if body.get("grant_type") != "client_credentials":
        return JSONResponse(
            {
                "error": "unsupported_grant_type",
                "error_description": 'Only grant_type "client_credentials" is supported.',
            },
            status_code=400,
        )

    cid = body.get("client_id")
    csec = body.get("client_secret")
    if not cid or not csec or str(cid).strip() != str(csec).strip():
        return JSONResponse(
            {
                "error": "invalid_client",
                "error_description": "client_id and client_secret must both be your Asterwise API key.",
            },
            status_code=401,
        )

    api_key = str(cid).strip()

    jwt_secret = os.getenv("JWT_SECRET")
    if not jwt_secret:
        return JSONResponse(
            {
                "error": "server_error",
                "error_description": "JWT_SECRET is not configured; Bearer tokens cannot be issued.",
            },
            status_code=503,
        )

    try:
        await _validate_api_key_with_asterwise(api_key)
    except AsterwiseAPIError as exc:
        return JSONResponse(
            {
                "error": "invalid_client",
                "error_description": str(exc),
            },
            status_code=401,
        )

    try:
        token = create_token(api_key)
    except AuthError as exc:
        return JSONResponse(
            {"error": "server_error", "error_description": str(exc)},
            status_code=503,
        )

    return JSONResponse(
        {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 3600,
        }
    )


if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8000"))
    mcp.run(transport="streamable-http", host=host, port=port)
