# asterwise-mcp Repository Audit

> **What this file is:** factual snapshot of the asterwise-mcp repo as it
> exists today. No opinions, no recommendations, no fixes. Pure description.
> If code changes, update this file. If the recommendation changes, update
> asterwise-api `_docs/audits/REPO_AUDIT_FINDINGS.md` instead.
>
> **Last audited:** 2026-05-21 (Pass 1 — structural baseline)
> **Auditor:** founder + Claude session
> **Commit at audit time:** `681a62c466e4c394aebdfcd856f077f7f242da57` — feat: add 3 MCP tools — varshaphal saham, harsha-bala, crystal natal recommendations
> **Scope:** asterwise-mcp repo only. Other repos audited separately.

---

## Overview

asterwise-mcp is the Model Context Protocol (MCP) server for Asterwise: it exposes
Vedic, Western, numerology, tarot, crystal, dream, and horoscope capabilities as
MCP tools with long structured `description=` strings for LLM clients. The stack
is Python 3.12 (`Dockerfile`), **FastMCP** (`fastmcp>=2.0.0` in `requirements.txt`;
local `.venv` reports **3.2.4**), Starlette/uvicorn ASGI, and **httpx** to proxy
almost all tool calls to **asterwise-api** (`ASTERWISE_API_BASE_URL`, default
`https://api.asterwise.com` in `.env.example`). Production is served at
**https://mcp.asterwise.com** on **Railway** (`railway.toml`, `Dockerfile` CMD
`uvicorn server:app --host 0.0.0.0 --port 8080`). The same process hosts MCP
(streamable HTTP), OAuth metadata/DCR/token endpoints, and an OAuth authorize
proxy to the marketing frontend (`FRONTEND_URL`, default `https://asterwise.com`)
so MCP clients (e.g. Claude.ai web) see `authorization_endpoint` on the MCP
domain. API keys are accepted via Bearer JWT or `X-API-Key`; OAuth issues MCP JWTs
after upstream token exchange.

---

## Top-level structure

```
total 392
drwxr-xr-x@ 29 Personal  staff    928 May  3 17:16 .
drwxr-xr-x  27 Personal  staff    864 May 19 14:48 ..
-rw-r--r--@  1 Personal  staff   8196 May 10 23:49 .DS_Store
-rw-r--r--@  1 Personal  staff  53248 May  3 17:16 .coverage
-rwxr-xr-x@  1 Personal  staff    137 Apr  1 16:21 .coveragerc
-rwxr-xr-x@  1 Personal  staff    330 Apr  1 16:40 .env.example
drwxr-xr-x@ 13 Personal  staff    416 May 21 15:15 .git
-rwxr-xr-x@  1 Personal  staff     85 Apr  1 14:56 .gitignore
drwxr-xr-x@  6 Personal  staff    192 Apr  1 14:38 .pytest_cache
-rwxr-xr-x@  1 Personal  staff      0 Apr  4 00:44 .railway-rebuild
drwxr-xr-x@  7 Personal  staff    224 Apr 25 08:44 .venv
-rwxr-xr-x@  1 Personal  staff    181 Apr  1 18:48 Dockerfile
-rwxr-xr-x@  1 Personal  staff   6086 Apr  1 14:56 README.md
drwxr-xr-x@ 10 Personal  staff    320 May  3 17:16 __pycache__
-rwxr-xr-x@  1 Personal  staff   6837 Apr  2 00:59 auth.py
-rwxr-xr-x@  1 Personal  staff   9702 Apr  2 00:44 client.py
-rwxr-xr-x@  1 Personal  staff    661 Apr  1 15:47 context.py
-rwxr-xr-x@  1 Personal  staff   1958 Apr  1 13:45 errors.py
drwxr-xr-x@  3 Personal  staff     96 Apr  1 14:53 evaluation
-rwxr-xr-x@  1 Personal  staff   2127 Apr  1 14:40 logging_config.py
-rwxr-xr-x@  1 Personal  staff  10435 May  1 20:28 models.py
-rwxr-xr-x@  1 Personal  staff    224 Apr  1 16:21 pytest.ini
-rwxr-xr-x@  1 Personal  staff    189 Apr  1 18:48 railway.toml
-rwxr-xr-x@  1 Personal  staff    227 Apr  4 00:50 requirements.txt
-rwxr-xr-x@  1 Personal  staff   6297 Apr  1 16:17 runtime.py
drwxr-xr-x@  2 Personal  staff     64 Apr  4 02:06 scripts
-rw-r--r--@  1 Personal  staff  41450 May  3 17:16 server.py
drwxr-xr-x@ 18 Personal  staff    576 Apr  1 16:19 tests
drwxr-xr-x@ 20 Personal  staff    640 May  3 15:51 tools
```

**Not present at repo root:** `main.py`, `app.py`, `pyproject.toml`, `setup.py`, `wrangler.toml`.

### `.gitignore`

```
__pycache__/
*.pyc
*.pyo
.env
.DS_Store
tools/__pycache__/
.coverage
.venv/
htmlcov/
```

---

## Server configuration

### FastMCP version

| Source | Value |
|---|---|
| `requirements.txt` | `fastmcp>=2.0.0` |
| `mcp[cli]>=1.0.0` | also declared |
| Local `.venv` (`pip show fastmcp`) | **3.2.4** |

### Entry point and registration pattern

| Item | Detail |
|---|---|
| ASGI entry | `server:app` (uvicorn / Railway / Docker) |
| FastMCP instance | `mcp = FastMCP("asterwise_mcp", instructions=…)` in `server.py` |
| MCP transport | `mcp.http_app(transport="streamable-http")` → `_mcp_asgi` |
| Tool registration | `_register_tools()` calls `register(mcp)` on 15 modules under `tools/` |
| Lifespan | Opens/closes `AsterwiseClient` (httpx) via `get_client()` |
| Auth middleware | `APIKeyASGIWrapper` + `CORSMiddleware` wrap `_dispatch_app` |
| Custom routes | Starlette `Router` for `/health`, OAuth metadata, `/authorize`, token, register, revoke; unmatched HTTP → FastMCP |

**`_register_tools()` module order:** `natal`, `varshaphal`, `dasha`, `matchmaking`, `panchanga`, `panchanga_ext`, `vedic_reference`, `yoga_dosha`, `numerology`, `numerology_gaps`, `angel_numbers`, `crystals`, `dreams`, `horoscope`, `western`, `tarot`.

**`server.py` instructions block** states **103 tools** (matches source count).

### Dockerfile / railway.toml

**Dockerfile:**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD uvicorn server:app --host 0.0.0.0 --port 8080
```

**railway.toml:**

```toml
[build]
builder = "DOCKERFILE"

[deploy]
startCommand = "uvicorn server:app --host 0.0.0.0 --port 8080"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
```

### Environment variables

From `.env.example` and code references:

| Variable | Role |
|---|---|
| `ASTERWISE_API_BASE_URL` | Upstream API base (e.g. `https://api.asterwise.com`) |
| `INTERNAL_API_TOKEN` | Bearer for proxying OAuth register/revoke/token to API |
| `JWT_SECRET` | MCP JWT sign/verify (min 32 chars) |
| `MCP_OAUTH_SECRET` | Documented for auth-code JWT alignment with API |
| `MCP_SERVER_HOST` / `MCP_SERVER_PORT` | Local `mcp.run()` defaults |
| `LOG_LEVEL` | Logging |
| `FRONTEND_URL` | OAuth authorize proxy target (default `https://asterwise.com`) |

---

## Source tree

```
.
./.pytest_cache
./.pytest_cache/v
./.pytest_cache/v/cache
./evaluation
./scripts
./tests
./tools
```

**Root Python modules (non-test):** `server.py`, `auth.py`, `client.py`, `context.py`, `errors.py`, `logging_config.py`, `models.py`, `runtime.py`.

**`tools/`:** 16 Python files (15 register modules + `__init__.py`).

**`tests/`:** 18 test modules (incl. `test_oauth_mcp.py`, `test_auth.py`, per-tool tests).

---

## Tool inventory

### Total tool count

| Metric | Count |
|---|---|
| `@mcp.tool(` registrations | **103** |
| Unique `name="asterwise_*"` | **103** |

### Tools by category

Heuristic grouping by tool name prefix/suffix (sums to 103):

| Category | Count |
|---|---|
| Numerology (+ angel, mobile/vehicle/business checks) | 21 |
| Western (+ biorhythm) | 18 |
| Natal / core Vedic (natal, divisional, strength, yogas, gochar, transits, remedies, etc.) | 15 |
| Tarot | 9 |
| Panchanga (+ choghadiya, hora, rahu kaal, muhurta, festival, Tamil) | 8 |
| Dasha (+ ghat chakra) | 7 |
| Crystals (+ gemstone recommendations) | 6 |
| Vedic reference (KP, Lal Kitab, nakshatra prediction, ayanamsha, planet nature, puja) | 5 |
| Yoga / dosha | 4 |
| Matchmaking | 4 |
| Varshaphal | 3 |
| Dreams | 2 |
| Horoscope (Vedic AI) | 1 |

### Tools per `tools/*.py` file

| File | `@mcp.tool` count |
|---|---|
| `tools/western.py` | 16 |
| `tools/natal.py` | 13 |
| `tools/numerology.py` | 11 |
| `tools/tarot.py` | 9 |
| `tools/vedic_reference.py` | 8 |
| `tools/numerology_gaps.py` | 7 |
| `tools/panchanga.py` | 6 |
| `tools/dasha.py` | 5 |
| `tools/matchmaking.py` | 5 |
| `tools/crystals.py` | 5 |
| `tools/varshaphal.py` | 3 |
| `tools/angel_numbers.py` | 3 |
| `tools/panchanga_ext.py` | 2 |
| `tools/dreams.py` | 2 |
| `tools/horoscope.py` | 4 |
| `tools/yoga_dosha.py` | 4 |
| `tools/__init__.py` | 0 |

### Files containing tool definitions

```
tools/angel_numbers.py
tools/crystals.py
tools/dasha.py
tools/dreams.py
tools/horoscope.py
tools/matchmaking.py
tools/natal.py
tools/numerology.py
tools/numerology_gaps.py
tools/panchanga.py
tools/panchanga_ext.py
tools/tarot.py
tools/varshaphal.py
tools/vedic_reference.py
tools/western.py
tools/yoga_dosha.py
```

### Full tool list (103, sorted)

```
asterwise_check_mobile_number
asterwise_check_sade_sati
asterwise_check_vehicle_number
asterwise_draw_tarot_cards
asterwise_get_angel_number
asterwise_get_angel_number_personal
asterwise_get_angel_number_today
asterwise_get_ashtakavarga
asterwise_get_ashtottari_dasha
asterwise_get_ayanamsha
asterwise_get_balance_number
asterwise_get_biorhythm
asterwise_get_business_name_analysis
asterwise_get_chaldean_numerology
asterwise_get_char_dasha
asterwise_get_chart_strength
asterwise_get_choghadiya
asterwise_get_compatibility
asterwise_get_crystal
asterwise_get_crystal_by_planet
asterwise_get_crystal_recommendations
asterwise_get_crystal_recommendations_natal
asterwise_get_crystals
asterwise_get_dasha
asterwise_get_dasha_transits
asterwise_get_dashakoot
asterwise_get_divisional_chart
asterwise_get_doshas
asterwise_get_dream_symbol
asterwise_get_dream_symbols
asterwise_get_expression_number
asterwise_get_festival_calendar
asterwise_get_gemstone_recommendations
asterwise_get_ghat_chakra
asterwise_get_gochar
asterwise_get_hora
asterwise_get_horoscope
asterwise_get_karmic_lessons
asterwise_get_kp_chart
asterwise_get_kp_ruling_planets
asterwise_get_kp_significators
asterwise_get_lal_kitab_chart
asterwise_get_lal_kitab_remedies
asterwise_get_lo_shu_grid
asterwise_get_lucky_numbers
asterwise_get_maturity_number
asterwise_get_muhurta
asterwise_get_nakshatra_details
asterwise_get_nakshatra_prediction
asterwise_get_name_correction
asterwise_get_natal_chart
asterwise_get_number_meaning
asterwise_get_numerology_compatibility
asterwise_get_numerology_profile
asterwise_get_panchanga
asterwise_get_panchanga_calendar
asterwise_get_papasamyam
asterwise_get_personal_cycles
asterwise_get_personal_year
asterwise_get_personality_number
asterwise_get_pitra_dosha
asterwise_get_planet_nature
asterwise_get_porutham
asterwise_get_prashna_chart
asterwise_get_puja_suggestions
asterwise_get_rahu_kaal
asterwise_get_remedies
asterwise_get_rudraksha
asterwise_get_soul_urge_number
asterwise_get_special_ascendants
asterwise_get_tamil_panchanga
asterwise_get_tarot_card
asterwise_get_tarot_card_of_the_day
asterwise_get_tarot_cards
asterwise_get_tarot_celtic_cross
asterwise_get_tarot_major_arcana
asterwise_get_tarot_suit
asterwise_get_tarot_three_card_spread
asterwise_get_tarot_yes_no
asterwise_get_thirumana_porutham
asterwise_get_transits
asterwise_get_varshaphal
asterwise_get_varshaphal_harsha_bala
asterwise_get_varshaphal_saham
asterwise_get_western_aspects
asterwise_get_western_compatibility
asterwise_get_western_composite
asterwise_get_western_horoscope
asterwise_get_western_lunar_return
asterwise_get_western_moon_calendar
asterwise_get_western_moon_phase
asterwise_get_western_natal
asterwise_get_western_planetary_return
asterwise_get_western_secondary_progressions
asterwise_get_western_solar_arc
asterwise_get_western_solar_return
asterwise_get_western_synastry
asterwise_get_western_transits_daily
asterwise_get_western_transits_monthly
asterwise_get_western_transits_weekly
asterwise_get_western_zodiac_compatibility
asterwise_get_yogas
asterwise_get_yogini_dasha
```

---

## Tool description quality

### SECTION: marker count

| Marker pattern | Occurrences |
|---|---|
| `SECTION: (WHAT\|WORKFLOW\|INPUT\|OUTPUT\|ERROR)` | **264** |
| `SECTION: WHAT` (per-file grep in `tools/`) | **103** (one per registered tool) |

Heuristic: 264 ÷ 5 ≈ **53** if each well-documented tool used exactly those five section headers once; actual tools use additional `SECTION:` lines inside ERROR blocks and related prose, so the divisor understates tools with partial section sets.

### Sample description lengths (`description=` string)

| Tool | Approx. length (chars) |
|---|---|
| `asterwise_get_natal_chart` | 5,015 |
| `asterwise_get_dasha` | 3,593 |
| `asterwise_get_horoscope` | 3,200 |
| `asterwise_get_panchanga` | 3,176 |
| `asterwise_get_yogas` | 2,793 |

---

## Auth / OAuth surface

### OAuth-related files

```
./auth.py
./tests/test_auth.py
./tests/test_oauth.py
./tests/test_oauth_mcp.py
./tests/test_runtime_auth.py
```

OAuth route handlers live primarily in **`server.py`** (not separate `oauth.py`).

### Redirect URI allowlist

| Rule | Implementation (`server.py`) |
|---|---|
| Custom scheme (explicit) | `cursor://anysphere.cursor-mcp/oauth/callback` in `ALLOWED_CUSTOM_SCHEME_URIS` |
| HTTPS | Any `https://` URI with host allowed |
| HTTP | Only `localhost`, `127.0.0.1`, `::1`, or `*.localhost` |
| No literal `claude.ai` string | Not found in redirect allowlist code; Claude web clients typically register `https://…` redirect URIs |

DCR validates each `redirect_uris` entry through `_redirect_uri_allowed()` before proxying upstream.

### Dynamic Client Registration (RFC 7591) support

| Item | Present |
|---|---|
| Metadata `registration_endpoint` | `https://mcp.asterwise.com/oauth/register` |
| Handler | `oauth_dynamic_client_register` on `POST /register` and `POST /oauth/register` |
| Upstream | Proxies to `{ASTERWISE_API_BASE_URL}/v1/oauth/register` with `INTERNAL_API_TOKEN` |
| Rate limit | `_oauth_rate_allow` (10/min per IP on register path) |

### PKCE support

| Item | Present |
|---|---|
| Metadata `code_challenge_methods_supported` | `["S256"]` |
| Tests | `tests/test_oauth_mcp.py` asserts S256 on metadata |

### OAuth metadata endpoints (production)

Live fetches at audit time returned JSON for:

- `GET /.well-known/oauth-authorization-server` — issuer `https://mcp.asterwise.com`, endpoints for authorize, token, register, revoke; grants `authorization_code`, `client_credentials`, `refresh_token`; scope `asterwise:read`
- `GET /.well-known/oauth-protected-resource` — resource `https://mcp.asterwise.com`, `authorization_servers` same host

Also registered in repo: `/mcp` suffixed well-known paths, OpenID configuration alias, `/authorize` + `/oauth/authorize` (302 proxy to `{FRONTEND_URL}/oauth/authorize`).

**`EXEMPT_PATHS` (no API key on MCP middleware):** `/`, `/health`, well-known OAuth paths, `/authorize`, `/token`, `/register`, `/oauth/register`, `/oauth/token`, `/oauth/revoke`, `/oauth/authorize`.

---

## Upstream API integration

### Asterwise-api URL configuration

| Mechanism | Detail |
|---|---|
| Env var | `ASTERWISE_API_BASE_URL` (required for `AsterwiseClient.__init__`) |
| Default in `.env.example` | `https://api.asterwise.com` |
| Health check | `GET {base}/health` from `health_check` in `server.py` |
| OAuth proxy paths | `/v1/oauth/register`, token/revoke flows via `_forward_upstream_json` |

### HTTP client library

| Library | Usage |
|---|---|
| **httpx** | `client.py` — `httpx.AsyncClient` with retries; `server.py` — ad hoc client for OAuth proxy and health |
| requests / aiohttp | not used in application code |

Tool handlers call `get_client().get()` / `.post()` with per-request API key from `require_api_key(ctx)`.

---

## Production parity check

Audit-time `curl` to **https://mcp.asterwise.com** (2026-05-21):

| Endpoint | Status / headers (summary) |
|---|---|
| `HEAD /` | **200**; `mcp-protocol-version: 2025-06-18`; `server: railway-edge` |
| `HEAD /mcp` | **401** JSON; `WWW-Authenticate: Bearer realm="Asterwise MCP", resource_metadata="https://mcp.asterwise.com/.well-known/oauth-protected-resource"` |
| `GET /.well-known/oauth-authorization-server` | **200** JSON (issuer, endpoints, S256, scopes) |
| `GET /.well-known/oauth-protected-resource` | **200** JSON (resource, authorization_servers, bearer header) |

Unauthenticated `/mcp` returning 401 with MCP WWW-Authenticate matches protected MCP entry in source.

---

## Repository totals

| Metric | Value |
|---|---|
| Files (excl. `.venv`, `__pycache__`, `.git`, `.pytest_cache`) | 51 |
| Python LOC (all `.py` under repo, incl. tests) | **9,698** |
| `server.py` LOC | ~1,132 |
| Disk usage (`du -sh .`) | 125M (includes `.venv`) |

---

## Existing documentation

**`_docs/` did not exist before this pass.** Created `_docs/audits/` for this audit.

**Other docs at repo root:** `README.md` (quick start, Claude Desktop / Cursor MCP config).

**Tests:** `tests/` (109 tests per last local run in sibling session); `evaluation/` directory present (contents not inventoried in Pass 1).

---

## Observations to investigate

- **103 tools in source**; `server.py` instructions and tool registrations agree. **`README.md` opening line says "52 tools"** — differs from current registration count.
- **`SECTION: WHAT` appears 103 times** (all tools); total `SECTION: (WHAT|WORKFLOW|INPUT|OUTPUT|ERROR)` count is **264**, not 515 — not every tool repeats all five section headers exactly once.
- **FastMCP** pinned `>=2.0.0`; installed **3.2.4** locally (not 3.2.0).
- **Redirect allowlist** allows any HTTPS URI; only **one** custom scheme URI is enumerated (`cursor://…`). No `claude.ai` hostname string in allowlist source.
- **OAuth authorize proxy** documents Claude.ai same-domain requirement; production metadata lists `authorization_endpoint` on `mcp.asterwise.com`.
- **Live `/mcp` without credentials** returns 401 — tool list enumeration on production requires auth (Pass 2 may compare live tool list vs 103).
- **`pyproject.toml` / `main.py`** absent; single entry `server:app` only.

---

*Next pass: Pass 2 — tool description completeness, category coverage gaps, auth surface verification.*
