# Asterwise MCP Server

Astrology and divination calculations as MCP tools. **103 tools** covering Vedic and Western astrology, numerology, tarot, crystals, dreams, natal charts, Dasha, matchmaking, Panchanga, and interpretations grounded in classical Jyotish methodology (BPHS, Phaladeepika).

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
        "MCP_HEADER_AUTHORIZATION": "Bearer your-api-key-here"
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
        "Authorization": "Bearer your-api-key-here"
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
Pass your Asterwise API key (starts with `aw_`) either as `Authorization: Bearer <api-key>` or as an `X-API-Key: <api-key>` header. Both are equivalent; use whichever your MCP client can set.

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

Access tokens are stateless HS256 JWTs. The API key is carried inside the token encrypted with a key derived from `JWT_SECRET`; only a SHA-256 hash of the key appears in the `sub` claim. Keep `JWT_SECRET` private.

## Configuration

Copy `.env.example` to `.env` and set at least:

| Variable | Required | Description |
|----------|----------|-------------|
| `ASTERWISE_API_BASE_URL` | Yes | Asterwise API base URL (e.g. `https://api.asterwise.com`). |
| `JWT_SECRET` | For `/oauth/token` | At least 32 characters; used to sign access tokens. |
| `MCP_SERVER_HOST` / `MCP_SERVER_PORT` | No | Bind address and port for the MCP HTTP server. |
| `LOG_LEVEL` | No | Default `INFO`. |

## Tools (103 total)

The MCP server exposes **103 tools** organized by Python module. The categorization reflects code organization; tools may serve multiple traditions (e.g. matchmaking includes both Sanskrit Dashakoot and Tamil Porutham methods).

- **western** — 16 tools (chart, transits, returns, progressions)
- **natal** — 13 tools (chart, dasha trees, ascendant systems)
- **numerology** — 11 tools (profile, compatibility, life path)
- **tarot** — 9 tools (draws, spreads, suit references)
- **vedic_reference** — 8 tools (nakshatra, planet nature, ayanamsha, classical reference)
- **numerology_gaps** — 7 tools (expression, soul urge, personality, maturity, balance, karmic, personal cycles)
- **panchanga** — 6 tools (panchanga, choghadiya, rahu kaal, hora)
- **crystals** — 5 tools (list, by planet, recommendations, individual)
- **dasha** — 5 tools (vimshottari, ashtottari, yogini, char, transits)
- **matchmaking** — 5 tools (dashakoot, porutham, thirumana, papasamyam, compatibility)
- **horoscope** — 4 tools (daily/weekly/monthly/yearly)
- **yoga_dosha** — 4 tools (yogas, doshas, sade sati, pitra dosha)
- **angel_numbers** — 3 tools (today, personal, lookup)
- **varshaphal** — 3 tools (annual chart, saham, harsha bala)
- **dreams** — 2 tools (symbols, individual)
- **panchanga_ext** — 2 tools (calendar, festivals, tamil)

For the full tool list see [docs.asterwise.com](https://docs.asterwise.com) or the MCP server's tool listing endpoint.

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
