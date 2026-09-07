# Asterwise MCP Server

[![Listed on mcpservers.org](https://mcpservers.org/badge.svg)](https://mcpservers.org/servers/asterwise/asterwise-mcp)

Astrology and divination calculations as MCP tools. **103 tools** covering Vedic and Western astrology, numerology, tarot, crystals, dreams, natal charts, Dasha, matchmaking and Panchanga, with interpretations that follow classical Jyotish method. Every position is verified against an independent Swiss Ephemeris run ([asterwise.com/proof](https://asterwise.com/proof/)) and checked against NASA JPL Horizons, median 0.046 arcseconds over 80 positions ([asterwise.com/accuracy](https://asterwise.com/accuracy/)).

## Quick Start (2 minutes)

See it first: [46-second demo of Claude Desktop casting a chart through this server](https://youtu.be/Oe17c6pXl8c), and the [independent Swiss Ephemeris cross-check](https://asterwise.com/proof/).

### Get your API key

Sign up free at [asterwise.com/dashboard](https://asterwise.com/dashboard): 500 calls/month on the Sandbox tier. No credit card. No time limit.

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

Three methods supported:

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

**Method 3 — OAuth 2.1 authorization code for MCP clients (Claude, Cursor, VS Code, Smithery)**  
MCP clients log a user in through the standard authorization-code flow with PKCE (`S256`). Discovery is at `/.well-known/oauth-authorization-server`. Two ways for a client to identify itself are supported:

- **Client ID Metadata Documents** (current MCP spec, preferred): use an HTTPS URL as `client_id`. The URL must serve a JSON document whose `client_id` equals the URL, with `client_name`, `redirect_uris`, and `token_endpoint_auth_method: "none"`. These clients are public: no secret, PKCE only, `authorization_code` and `refresh_token` grants, refresh tokens rotate on every use. Redirect URIs must be `https`, or `http` on `localhost` / `127.0.0.1` / `[::1]` (port ignored, per RFC 8252). A reference document you can copy: <https://asterwise.com/public/oauth/example-client.json>.
- **Dynamic Client Registration** (`POST /oauth/register`, deprecated in the MCP spec but still supported): returns a `client_id` and `client_secret`; the secret is required at `/oauth/token`.

The server fetches metadata documents with SSRF protections (public addresses only, no redirects, 64 KB, 10 s) and caches them for the document's `Cache-Control: max-age` (60 s to 24 h, default 1 h). The consent page shows the host that published the document.

## Run over stdio

For hosts that speak stdio instead of HTTP (Glama hosted builds, a local Claude Desktop entry, quick tests):

```bash
pip install -r requirements.txt
ASTERWISE_API_KEY=aw_your_key python stdio.py
```

Over stdio the key comes from `ASTERWISE_API_KEY`; the server starts and lists its tools without one, and tool calls need it. Logs go to stderr.

## Configuration

Copy `.env.example` to `.env` and set at least:

| Variable | Required | Description |
|----------|----------|-------------|
| `ASTERWISE_API_BASE_URL` | Yes | Asterwise API base URL (e.g. `https://api.asterwise.com`). |
| `JWT_SECRET` | For `/oauth/token` | At least 32 characters; used to sign access tokens. |
| `MCP_SERVER_HOST` / `MCP_SERVER_PORT` | No | Bind address and port for the MCP HTTP server. |
| `LOG_LEVEL` | No | Default `INFO`. |
| `MCP_OAUTH_SECRET` | For OAuth | Shared with asterwise-api; verifies access tokens issued by its `/v1/oauth/token`. |
| `ASTERWISE_API_KEY` | stdio only | Your Asterwise API key for `python stdio.py`; HTTP deployments take the key per request instead. |
| `INTERNAL_API_TOKEN` | For OAuth client registration | Shared with asterwise-api; used when forwarding dynamic client registration. |
| `FRONTEND_URL` | For `/authorize` | Where the browser is sent for sign-in and consent (e.g. `https://asterwise.com`). |
| `OPENAI_APPS_CHALLENGE_TOKEN` | No | Served at `/.well-known/openai-apps-challenge` for directory verification. |

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
pip install -r requirements-dev.txt
export ASTERWISE_API_BASE_URL=https://api.asterwise.com
export JWT_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
uvicorn server:app --host 0.0.0.0 --port 8080
```

`uvicorn server:app` is the same entry point the production `Dockerfile` and `railway.toml` use, so the auth middleware, OAuth routes and `/health` are all present locally. Runtime dependencies are pinned in `requirements.txt`; `requirements-dev.txt` adds the test tooling.

## Tests

```bash
pytest
```

Coverage is enforced at **78%** for core modules (`auth`, `client`, `errors`, `logging_config`, `models`, `runtime`, `server`); tool modules are excluded from the gate (see `.coveragerc`).

## Status

[https://status.asterwise.com](https://status.asterwise.com)

## License

MIT. See [LICENSE](LICENSE). Security reports: see [SECURITY.md](SECURITY.md).
