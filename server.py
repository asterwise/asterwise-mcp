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
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from context import set_request_api_key
from middleware.security_headers import SecurityHeadersASGIWrapper

load_dotenv()

from logging_config import configure_logging

configure_logging()

from auth import TOKEN_TTL, _token_cache, create_token
from client import get_client
from errors import AsterwiseAPIError
from tools import (
    angel_numbers, crystals, dasha, dreams, horoscope, matchmaking, natal,
    numerology, numerology_gaps, panchanga, panchanga_ext, tarot, vedic_reference,
    varshaphal, western, yoga_dosha,
)

logger = logging.getLogger("asterwise_mcp.server")

# Returned when Content-Type is JSON but the body is not valid JSON (OAuth invalid_request).
_JSON_BODY_PARSE_FAILED = object()


def _is_json_content_type(content_type: str) -> bool:
    base = content_type.lower().split(";")[0].strip()
    return base == "application/json" or base.endswith("+json")


async def _parse_request_body(request: Request) -> Any:
    """Parse request body as form-encoded or JSON (dict, or JSON list for caller to reject)."""
    content_type = request.headers.get("content-type", "").lower().split(";")[0].strip()

    if content_type == "application/x-www-form-urlencoded":
        form = await request.form()
        return {str(k): str(v) for k, v in form.items()}

    if _is_json_content_type(content_type):
        try:
            body = await request.json()
            if isinstance(body, dict):
                return body
            return body
        except Exception:
            return _JSON_BODY_PARSE_FAILED

    try:
        body = await request.json()
        if isinstance(body, dict):
            return body
        return body
    except Exception:
        pass

    try:
        form = await request.form()
        if form:
            return {str(k): str(v) for k, v in form.items()}
    except Exception:
        pass

    return {}


# Public routes (no API key / Bearer required). OAuth discovery and token endpoints.
EXEMPT_PATHS = frozenset(
    {
        "/",
        "/health",
        "/.well-known/oauth-authorization-server",
        "/.well-known/oauth-authorization-server/mcp",
        "/.well-known/openid-configuration",
        "/.well-known/oauth-protected-resource",
        "/.well-known/oauth-protected-resource/mcp",
        "/.well-known/glama.json",
        "/.well-known/openai-apps-challenge",
        "/authorize",
        "/token",
        "/register",
        "/oauth/register",
        "/oauth/token",
        "/oauth/revoke",
        "/oauth/authorize",
    }
)

_WWW_AUTHENTICATE_MCP = (
    'Bearer realm="Asterwise MCP", '
    'resource_metadata="https://mcp.asterwise.com/.well-known/oauth-protected-resource"'
)


class APIKeyASGIWrapper:
    """Bearer / X-API-Key → ContextVar; 401 when required auth is missing (pure ASGI)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET")
        logger.debug(
            "middleware_auth_enter",
            extra={"path": path, "method": method},
        )

        hdr = Headers(scope=scope)
        api_key: str | None = None
        auth_header = hdr.get("authorization", "")
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

        xkey_present = bool(hdr.get("x-api-key", "").strip())
        if not api_key:
            api_key = hdr.get("x-api-key", "").strip() or None

        if path not in EXEMPT_PATHS and method != "OPTIONS" and api_key is None:
            resp = JSONResponse(
                {
                    "error": "unauthorized",
                    "error_description": (
                        "Authentication required. "
                        "Get a free API key at "
                        "asterwise.com/dashboard "
                        "or connect via OAuth."
                    ),
                },
                status_code=401,
                headers={
                    "WWW-Authenticate": _WWW_AUTHENTICATE_MCP,
                    "Content-Type": "application/json",
                },
            )
            await resp(scope, receive, send)
            return

        set_request_api_key(api_key)
        logger.debug(
            "middleware_auth",
            extra={
                "path": path,
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
            await self.app(scope, receive, send)
        finally:
            set_request_api_key(None)


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
    token = os.getenv("INTERNAL_API_TOKEN", "").strip()
    if not token:
        return None
    return {"Authorization": f"Bearer {token}"}


# Cursor's fixed MCP OAuth callback URI uses a custom scheme.
ALLOWED_CUSTOM_SCHEME_URIS = frozenset([
    "cursor://anysphere.cursor-mcp/oauth/callback",
])


def _redirect_uri_allowed(uri: str) -> bool:
    if uri.strip() in ALLOWED_CUSTOM_SCHEME_URIS:
        return True
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
  You are connected to the Asterwise Astrology and Divination API — the most
  comprehensive structured astrology MCP available.

  This server exposes 103 tools. All tools require an API key
  obtained from asterwise.com.

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DOMAIN 1 — VEDIC ASTROLOGY (sidereal)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  asterwise_get_natal_chart — full sidereal natal chart (planets, houses, drishti, arudhas, bhava cusps)
  asterwise_get_divisional_chart — one or all 16 divisional charts (D1–D60); omit chart_type for all 16
  asterwise_get_chart_strength — Shadbala, Bhavbala, Vimshopaka scores
  asterwise_get_yogas — classical yoga detection (raja, dhana, mahapurusha, etc.)
  asterwise_get_doshas — 12 dosha analysis
  asterwise_get_dasha — 5-level Vimshottari Dasha tree
  asterwise_get_ashtottari_dasha — Ashtottari 108-year dasha
  asterwise_get_yogini_dasha — 8-Yogini 36-year dasha
  asterwise_get_char_dasha — Char Dasha
  asterwise_get_dasha_transits — dasha-lord transit correlation
  asterwise_get_gochar — 9-planet Gochar with AVK scores and vedha
  asterwise_get_transits — ingress and station event tables
  asterwise_get_ashtakavarga — bindu matrices, trikona/ekadhipatya reductions
  asterwise_get_varshaphal — Tajika annual solar return
  asterwise_get_varshaphal_saham — 10 Tajika Saham sensitive points (Arabic Parts equivalent) for a solar return: Punya/Fortune, Vidya/Education, Yashas/Fame, Mitra/Friends, Mahatmya/Status, Asha/Desires, Karmakarya/Career, Vyapara/Business, Vivaha/Marriage, Santapa/Sorrow
  asterwise_get_varshaphal_harsha_bala — Harsha Bala positional happiness score (0–20) for all 7 classical planets in the Varsha chart: 4 components × 5 points (Sthana, Swakshetra/Uccha, Pum-Stri, Dina-Ratri)
  asterwise_get_special_ascendants — Atmakaraka + Ishta Devata
  asterwise_get_nakshatra_details — 27-nakshatra encyclopaedia
  asterwise_get_gemstone_recommendations — classical Ratna prescriptions
  asterwise_get_remedies — mantra, gem, and charity remedies
  asterwise_get_panchanga — daily Panchanga (tithi, vara, nakshatra, yoga, karana)
  asterwise_get_panchanga_calendar — monthly Panchanga calendar
  asterwise_get_muhurta — auspicious timing search
  asterwise_get_choghadiya — 16-segment day Choghadiya
  asterwise_get_hora — 24-planetary Hora table
  asterwise_get_rahu_kaal — Rahu Kaal, Gulika Kaal, Yamaganda
  asterwise_get_tamil_panchanga — Tamil panchanga: Rahu Kalam, Yamagandam, Kuligai, Emagandam, Nalla Neram, Tamil solar month
  asterwise_get_festival_calendar — Hindu festival calendar for a year: 20 festivals computed astronomically (no hardcoded dates)
  asterwise_get_kp_chart — KP natal chart with sub-lords
  asterwise_get_kp_significators — KP house significator chains
  asterwise_get_kp_ruling_planets — instantaneous KP ruling planets
  asterwise_get_lal_kitab_chart — Lal Kitab chart and Rin analysis
  asterwise_get_lal_kitab_remedies — Lal Kitab totkas
  asterwise_get_prashna_chart — Prashna (horary) chart
  asterwise_check_sade_sati — Saturn Sade Sati phases and intensity
  asterwise_get_compatibility — Ashtakoota Guna Milan matchmaking
  asterwise_get_dashakoot — 10-koota Dashakoot scoring
  asterwise_get_porutham — Tamil 10-porutham with Rajju/Vedha vetoes
  asterwise_get_thirumana_porutham — Tamil 12-porutham
  asterwise_get_papasamyam — Papasamyam malefic balance
  asterwise_get_horoscope — AI moon-sign horoscope (daily/weekly/monthly/yearly)

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DOMAIN 2 — WESTERN ASTROLOGY (tropical)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  asterwise_get_western_natal — tropical natal chart (10 planets, dignities, aspects, elements)
  asterwise_get_western_aspects — aspect grid from raw longitudes
  asterwise_get_western_moon_phase — lunar phase for any date
  asterwise_get_western_moon_calendar — monthly lunar phase calendar
  asterwise_get_western_transits_daily — daily transits vs natal
  asterwise_get_western_transits_weekly — 7-day transit window
  asterwise_get_western_transits_monthly — 30-day transit window
  asterwise_get_western_synastry — inter-chart aspect grid (two people)
  asterwise_get_western_composite — midpoint composite chart (method)
  asterwise_get_western_compatibility — compatibility score 0-100
  asterwise_get_western_zodiac_compatibility — sign-to-sign affinity (no birth data needed)
  asterwise_get_western_solar_return — solar return chart for a given year
  asterwise_get_western_lunar_return — next lunar return chart
  asterwise_get_western_planetary_return — next return chart for any planet
  asterwise_get_western_secondary_progressions — day-for-a-year progressed chart
  asterwise_get_western_solar_arc — Solar Arc Directions

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DOMAIN 3 — NUMEROLOGY
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  asterwise_get_numerology_profile — full Pythagorean profile (LP, Expression, Soul Urge, etc.)
  asterwise_get_expression_number — Expression number from name
  asterwise_get_soul_urge_number — Soul Urge from vowels
  asterwise_get_personality_number — Personality from consonants
  asterwise_get_maturity_number — Maturity (LP + Expression)
  asterwise_get_balance_number — Balance from initials
  asterwise_get_karmic_lessons — missing digit analysis
  asterwise_get_personal_cycles — Personal Year, Month, Day
  asterwise_get_personal_year — Personal Year theme
  asterwise_get_numerology_compatibility — two-person Life Path comparison
  asterwise_get_chaldean_numerology — Chaldean letter-value system
  asterwise_get_lo_shu_grid — Lo Shu magic square from birth digits
  asterwise_get_name_correction — spelling harmony scoring
  asterwise_get_lucky_numbers — numerology lucky number set
  asterwise_get_number_meaning — dictionary entry for any number 1-33
  asterwise_check_mobile_number — phone number harmony analysis
  asterwise_check_vehicle_number — vehicle plate digit analysis
  asterwise_get_business_name_analysis — business name Expression scoring
  asterwise_get_angel_number_today — today's collective angel number from the current date
  asterwise_get_angel_number — lookup a specific angel number sequence (111, 444, 999, 1111, etc.)
  asterwise_get_angel_number_personal — personal angel number from birth date Life Path

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CRYSTALS
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  asterwise_get_crystals — complete crystal database: 50 crystals with Vedic and Western planetary assignments
  asterwise_get_crystal — single crystal lookup by slug or name
  asterwise_get_crystal_by_planet — crystals filtered by Vedic planet (Navaratna first)
  asterwise_get_crystal_recommendations — crystal recommendations by zodiac sign, chakra, or intention
  asterwise_get_crystal_recommendations_natal — natal chart crystal recommendations from house lordship rules on a computed Vedic natal chart; Lagna lord (Life Stone), 9th lord (Fortune Stone), 5th lord (Lucky Stone), Yogakaraka (supreme benefic); only navaratna and uparatna crystals returned; dangerous combinations flagged in warnings[]

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DREAMS
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  asterwise_get_dream_symbols — 500 dream symbols with dual Jungian + Vedic dream interpretation
  asterwise_get_dream_symbol — single dream symbol lookup with context variants and traditions_agree flag

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DOMAIN 4 — TAROT (Rider-Waite-Smith, 78 cards)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  asterwise_get_tarot_cards — complete 78-card catalogue
  asterwise_get_tarot_card — single card by slug ID
  asterwise_get_tarot_major_arcana — 22 Major Arcana
  asterwise_get_tarot_suit — 14 cards by suit (wands/cups/swords/pentacles)
  asterwise_get_tarot_card_of_the_day — deterministic daily card (SHA-256 seeded)
  asterwise_draw_tarot_cards — random draw of N cards (cryptographic randomness)
  asterwise_get_tarot_three_card_spread — Past/Present/Future spread
  asterwise_get_tarot_celtic_cross — 10-card Celtic Cross spread
  asterwise_get_tarot_yes_no — single-card yes/no answer with confidence

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RULES
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Vedic tools: always use lahiri ayanamsa unless user specifies kp, raman, or tropical.
  Western tools: always tropical zodiac. house_system defaults to placidus.
  Matchmaking: check Rajju and Vedha vetoes first. A failed veto overrides Guna score regardless of total.
  Birth data format: date=YYYY-MM-DD, time=HH:MM (24h local), lat/lon decimal degrees, timezone=IANA string.
  If user gives a city name only: ask for coordinates. The API requires decimal degrees.
  All tools support response_format=json (structured) or response_format=markdown (human-readable).
  """,
    lifespan=lifespan,
)


def _register_tools() -> None:
    natal.register(mcp)
    varshaphal.register(mcp)
    dasha.register(mcp)
    matchmaking.register(mcp)
    panchanga.register(mcp)
    panchanga_ext.register(mcp)
    vedic_reference.register(mcp)
    yoga_dosha.register(mcp)
    numerology.register(mcp)
    numerology_gaps.register(mcp)
    angel_numbers.register(mcp)
    crystals.register(mcp)
    dreams.register(mcp)
    horoscope.register(mcp)
    western.register(mcp)
    tarot.register(mcp)


_register_tools()


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


async def oauth_metadata(request: Request) -> Response:
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    _ = request
    return JSONResponse(
        {
            "issuer": "https://mcp.asterwise.com",
            "authorization_endpoint": "https://mcp.asterwise.com/authorize",
            "token_endpoint": "https://mcp.asterwise.com/oauth/token",
            "registration_endpoint": "https://mcp.asterwise.com/oauth/register",
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


async def openid_metadata(request: Request) -> Response:
    """OpenID Connect Discovery (for broad compatibility)."""
    _ = request
    return JSONResponse(
        {
            "issuer": "https://mcp.asterwise.com",
            "authorization_endpoint": "https://mcp.asterwise.com/authorize",
            "token_endpoint": "https://mcp.asterwise.com/oauth/token",
            "registration_endpoint": "https://mcp.asterwise.com/oauth/register",
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


async def glama_metadata(request: Request) -> Response:
    """Glama MCP server claim verification (https://glama.ai)."""
    _ = request
    return JSONResponse(
        {
            "$schema": "https://glama.ai/mcp/schemas/connector.json",
            "maintainers": [
                {"email": "asterwiselabs@gmail.com"},
            ],
        }
    )


async def openai_apps_challenge(request: Request) -> Response:
    """OpenAI Apps domain verification challenge (plain text token)."""
    _ = request
    token = os.getenv("OPENAI_APPS_CHALLENGE_TOKEN", "").strip()
    if not token:
        return Response(status_code=404)
    return Response(
        content=token,
        status_code=200,
        media_type="text/plain",
    )


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
        body = await _parse_request_body(request)

        if body is _JSON_BODY_PARSE_FAILED:
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
        body = await _parse_request_body(request)

        if body is _JSON_BODY_PARSE_FAILED:
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
                "/v1/account",
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


async def oauth_authorize_proxy(request: Request) -> Response:
    """
    Proxy OAuth authorization to asterwise.com consent page.
    Claude.ai requires authorization_endpoint on same domain
    as the MCP server.
    """
    query_string = str(request.url.query)
    frontend_url = os.getenv(
        "FRONTEND_URL", "https://asterwise.com"
    ).rstrip("/")
    redirect_url = (
        f"{frontend_url}/oauth/authorize"
        f"?{query_string}" if query_string
        else f"{frontend_url}/oauth/authorize"
    )
    return Response(
        status_code=302,
        headers={"Location": redirect_url}
    )


async def head_handler(request: Request) -> Response:
    _ = request
    return Response(
        status_code=200,
        headers={
            "MCP-Protocol-Version": "2025-06-18",
        }
    )


# Public ASGI app — explicit custom Router first; everything else to FastMCP (no greedy Mount("/")).
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route, Router

# FastMCP ASGI app — MCP protocol + lifespan (session manager, httpx client).
_mcp_asgi = mcp.http_app(transport="streamable-http")

_custom_route_keys = frozenset(
    {
        ("/", "HEAD"),
        ("/health", "GET"),
        ("/health", "HEAD"),
        ("/.well-known/oauth-authorization-server", "GET"),
        ("/.well-known/oauth-authorization-server/mcp", "GET"),
        ("/.well-known/openid-configuration", "GET"),
        ("/.well-known/oauth-protected-resource", "GET"),
        ("/.well-known/oauth-protected-resource/mcp", "GET"),
        ("/.well-known/glama.json", "GET"),
        ("/.well-known/openai-apps-challenge", "GET"),
        ("/authorize", "GET"),
        ("/token", "POST"),
        ("/register", "POST"),
        ("/oauth/authorize", "GET"),
        ("/oauth/register", "POST"),
        ("/oauth/token", "POST"),
        ("/oauth/revoke", "POST"),
    }
)
_custom_paths = frozenset(p for p, _ in _custom_route_keys)

_custom_routes = [
    Route(
        "/",
        endpoint=head_handler,
        methods=["HEAD"],
    ),
    Route(
        "/health",
        endpoint=health_check,
        methods=["GET", "HEAD"],
    ),
    Route(
        "/.well-known/oauth-authorization-server",
        endpoint=oauth_metadata,
        methods=["GET"],
    ),
    Route(
        "/.well-known/oauth-authorization-server/mcp",
        endpoint=oauth_metadata,
        methods=["GET"],
    ),
    Route(
        "/.well-known/openid-configuration",
        endpoint=openid_metadata,
        methods=["GET"],
    ),
    Route(
        "/.well-known/oauth-protected-resource",
        endpoint=oauth_protected_resource_metadata,
        methods=["GET"],
    ),
    Route(
        "/.well-known/oauth-protected-resource/mcp",
        endpoint=oauth_protected_resource_metadata,
        methods=["GET"],
    ),
    Route(
        "/.well-known/glama.json",
        endpoint=glama_metadata,
        methods=["GET"],
    ),
    Route(
        "/.well-known/openai-apps-challenge",
        endpoint=openai_apps_challenge,
        methods=["GET"],
    ),
    Route(
        "/authorize",
        endpoint=oauth_authorize_proxy,
        methods=["GET"],
    ),
    Route(
        "/token",
        endpoint=oauth_token,
        methods=["POST"],
    ),
    Route(
        "/register",
        endpoint=oauth_dynamic_client_register,
        methods=["POST"],
    ),
    Route(
        "/oauth/authorize",
        endpoint=oauth_authorize_proxy,
        methods=["GET"],
    ),
    Route(
        "/oauth/register",
        endpoint=oauth_dynamic_client_register,
        methods=["POST"],
    ),
    Route(
        "/oauth/token",
        endpoint=oauth_token,
        methods=["POST"],
    ),
    Route(
        "/oauth/revoke",
        endpoint=oauth_revoke,
        methods=["POST"],
    ),
]

_custom_router = Router(routes=_custom_routes)


async def _dispatch_app(scope: Scope, receive: Receive, send: Send) -> None:
    """Lifespan → FastMCP; HTTP → custom routes when path+method match, else FastMCP."""
    if scope["type"] == "lifespan":
        await _mcp_asgi(scope, receive, send)
        return
    if scope["type"] == "websocket":
        await _mcp_asgi(scope, receive, send)
        return
    if scope["type"] != "http":
        await _mcp_asgi(scope, receive, send)
        return

    path = scope.get("path", "")
    method = scope.get("method", "GET")
    if (path, method) in _custom_route_keys or (
        method == "OPTIONS" and path in _custom_paths
    ):
        await _custom_router(scope, receive, send)
        return
    await _mcp_asgi(scope, receive, send)


# CORS outermost, then security headers, then API key auth, then dispatch.
app = CORSMiddleware(
    SecurityHeadersASGIWrapper(APIKeyASGIWrapper(_dispatch_app)),
    allow_origins=["*"],
    allow_methods=["GET", "HEAD", "POST", "OPTIONS", "DELETE"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "Accept",
        "Mcp-Session-Id",
    ],
    expose_headers=["Mcp-Session-Id", "WWW-Authenticate"],
    allow_credentials=False,
)


if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8000"))
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
    )
