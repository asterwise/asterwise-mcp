# Asterwise MCP Server

Classical Vedic astrology calculations as MCP tools. **52 tools** covering natal charts, Dasha, matchmaking, Panchanga, numerology, and interpretations — derived from BPHS, Phaladeepika, and Saravali with citations.

## Quick Start (2 minutes)

### Get your API key

Sign up free at [asterwise.com/dashboard](https://asterwise.com/dashboard): 2,000 calls/month. No credit card. No time limit.

### Connect to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "asterwise": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://mcp.asterwise.com/mcp"
      ],
      "env": {
        "MCP_HEADER_X_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Connect to Cursor

Add to `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "asterwise": {
      "url": "https://mcp.asterwise.com/mcp",
      "headers": {
        "X-API-Key": "your-api-key-here"
      }
    }
  }
}
```

### Test the connection

```bash
curl https://mcp.asterwise.com/health
```

## Authentication

Two methods supported:

**Method 1 — API Key (quick start)**  
Pass `X-API-Key` with your Asterwise API key.

**Method 2 — OAuth 2.1 (production)**  
Exchange your API key for a short-lived token:

```bash
curl -X POST https://mcp.asterwise.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "your-api-key",
    "client_secret": "your-api-key"
  }'
```

Returns: `{"access_token": "...", "expires_in": 3600, ...}`

Use the token: `Authorization: Bearer <access_token>`

JWTs issued by this server store only a **SHA-256 hash** of the API key server-side; the raw key is never embedded in the token payload.

## Configuration

Copy `.env.example` to `.env` and set at least:

| Variable | Required | Description |
|----------|----------|-------------|
| `ASTERWISE_API_BASE_URL` | Yes | Asterwise API base URL (e.g. `https://api.asterwise.com`). |
| `JWT_SECRET` | For `/oauth/token` | At least 32 characters; used to sign access tokens. |
| `MCP_SERVER_HOST` / `MCP_SERVER_PORT` | No | Bind address and port for the MCP HTTP server. |
| `LOG_LEVEL` | No | Default `INFO`. |

## Tools Reference (52 tools)

### Natal & charts (14)

- `asterwise_get_natal_chart` — Full natal chart (BPHS-style).
- `asterwise_get_divisional_chart` — Varga / divisional charts (D1–D60).
- `asterwise_get_chart_strength` — Shadbala / Bhavbala.
- `asterwise_get_special_ascendants` — Atmakaraka and Ishta Devata.
- `asterwise_get_nakshatra_details` — Nakshatra reference profile.
- `asterwise_check_sade_sati` — Sade Sati status.
- `asterwise_get_prashna_chart` — Prashna (horary) chart.
- `asterwise_get_varshaphal` — Varshaphal (solar return).
- `asterwise_get_lal_kitab_chart` — Lal Kitab chart.
- `asterwise_get_lal_kitab_remedies` — Lal Kitab remedies.
- `asterwise_get_kp_chart` — KP chart.
- `asterwise_get_kp_significators` — KP significators.
- `asterwise_get_kp_ruling_planets` — KP ruling planets.
- `asterwise_get_ashtakavarga` — Ashtakavarga tables.

### Dasha (5)

- `asterwise_get_dasha` — Vimshottari Dasha (multi-level).
- `asterwise_get_dasha_transits` — Transits within Dasha periods.
- `asterwise_get_char_dasha` — Char (Jaimini) Dasha.
- `asterwise_get_yogini_dasha` — Yogini Dasha.
- `asterwise_get_ashtottari_dasha` — Ashtottari Dasha.

### Matchmaking (5)

- `asterwise_get_compatibility` — Ashtakoota with Rajju / Vedha vetoes.
- `asterwise_get_dashakoot` — Dashakoot compatibility.
- `asterwise_get_papasamyam` — Papa Samyam.
- `asterwise_get_porutham` — Tamil Porutham.
- `asterwise_get_thirumana_porutham` — Thirumana Porutham.

### Yogas & doshas (4)

- `asterwise_get_yogas` — Yoga detection.
- `asterwise_get_doshas` — Dosha analysis.
- `asterwise_get_remedies` — Remedial guidance.
- `asterwise_get_gemstone_recommendations` — Gemstone suggestions.

### Panchanga & timing (6)

- `asterwise_get_panchanga` — Daily Panchanga.
- `asterwise_get_choghadiya` — Choghadiya periods.
- `asterwise_get_hora` — Planetary hora.
- `asterwise_get_rahu_kaal` — Rahu Kaal.
- `asterwise_get_muhurta` — Muhurta windows.
- `asterwise_get_panchanga_calendar` — Monthly Panchanga calendar.

### Horoscope & transits (3)

- `asterwise_get_horoscope` — Sign-based horoscope (daily/weekly/monthly/yearly).
- `asterwise_get_gochar` — Gochar (transit) snapshot.
- `asterwise_get_transits` — Current transits detail.

### Numerology (11)

- `asterwise_get_numerology_profile` — Full numerology profile.
- `asterwise_get_numerology_compatibility` — Relationship compatibility.
- `asterwise_get_chaldean_numerology` — Chaldean analysis.
- `asterwise_get_lo_shu_grid` — Lo Shu grid.
- `asterwise_get_name_correction` — Name correction suggestions.
- `asterwise_get_lucky_numbers` — Lucky numbers.
- `asterwise_get_personal_year` — Personal year cycle.
- `asterwise_get_number_meaning` — Single number meaning.
- `asterwise_check_mobile_number` — Mobile number analysis.
- `asterwise_check_vehicle_number` — Vehicle number analysis.
- `asterwise_get_business_name_analysis` — Business name analysis.

### Reports (4)

- `asterwise_generate_kundli_report` — Kundli PDF report.
- `asterwise_generate_matchmaking_report` — Matchmaking report.
- `asterwise_generate_dasha_report` — Dasha report.
- `asterwise_generate_varshaphal_report` — Varshaphal report.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ASTERWISE_API_BASE_URL=https://api.asterwise.com
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python server.py
```

## Tests

```bash
pytest
```

Coverage is enforced at **80%** for core modules (`auth`, `client`, `errors`, `logging_config`, `models`, `runtime`, `server`); tool modules are excluded from the gate (see `.coveragerc`).

## Status

[https://status.asterwise.com](https://status.asterwise.com)
