"""Asterwise MCP server — streamable HTTP transport, tools, OAuth token, health."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

load_dotenv()

from auth import create_token
from client import get_client
from errors import AsterwiseAPIError
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


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> Response:
    return JSONResponse({"status": "ok", "version": "1.0.0"})


@mcp.custom_route("/oauth/token", methods=["POST"])
async def oauth_token(request: Request) -> Response:
    """OAuth 2.1-style client_credentials using the API key as both id and secret."""
    try:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                {
                    "error": "invalid_request",
                    "error_description": "Request body must be valid JSON object",
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

        if body.get("grant_type") != "client_credentials":
            return JSONResponse(
                {
                    "error": "unsupported_grant_type",
                    "error_description": "Only client_credentials grant type is supported",
                },
                status_code=400,
            )

        client_id = str(body.get("client_id", "")).strip()
        client_secret = str(body.get("client_secret", "")).strip()

        if not client_id or not client_secret:
            return JSONResponse(
                {
                    "error": "invalid_client",
                    "error_description": "client_id and client_secret are required",
                },
                status_code=401,
            )

        if client_id != client_secret:
            return JSONResponse(
                {
                    "error": "invalid_client",
                    "error_description": "client_id and client_secret must match your Asterwise API key",
                },
                status_code=401,
            )

        try:
            await get_client().get("/v1/numerology/meaning/1", client_id)
        except AsterwiseAPIError as e:
            return JSONResponse(
                {"error": "invalid_client", "error_description": str(e)},
                status_code=401,
            )
        except httpx.TimeoutException:
            return JSONResponse(
                {
                    "error": "temporarily_unavailable",
                    "error_description": "Upstream validation timed out. Try again shortly.",
                },
                status_code=503,
            )
        except Exception:
            return JSONResponse(
                {
                    "error": "server_error",
                    "error_description": "Token issuance failed. Check status.asterwise.com",
                },
                status_code=500,
            )

        try:
            token = create_token(client_id)
        except Exception:
            return JSONResponse(
                {
                    "error": "server_error",
                    "error_description": "JWT_SECRET not configured. Contact support.",
                },
                status_code=503,
            )

        return JSONResponse(
            {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": 3600,
            }
        )
    except Exception:
        return JSONResponse(
            {
                "error": "server_error",
                "error_description": "Token endpoint failed. Check status.asterwise.com",
            },
            status_code=500,
        )


if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8000"))
    mcp.run(transport="streamable-http", host=host, port=port)
