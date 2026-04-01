# Asterwise MCP

Remote [Model Context Protocol](https://modelcontextprotocol.io) server that exposes the **Asterwise Vedic astrology REST API** as tools for LLM clients (Claude, GPT, and any MCP-compatible client).

This repository is a standalone Python service. It does not include the Asterwise API implementation.

## Features

- **Streamable HTTP** MCP transport (`transport="streamable-http"`), not SSE.
- **Stateless proxy**: API keys are sent by the client per request (`X-API-Key` or Bearer JWT), not stored in environment variables.
- **52 read tools** covering natal charts, divisional charts, Dasha systems, matchmaking, Panchanga, yogas/doshas, numerology, horoscopes, transits, and PDF reports.

## Configuration (environment)

| Variable | Required | Description |
|----------|----------|-------------|
| `ASTERWISE_API_BASE_URL` | Yes | Base URL of the Asterwise API (e.g. `https://api.asterwise.com`). |
| `MCP_SERVER_HOST` | No | Bind address (default `0.0.0.0`). |
| `MCP_SERVER_PORT` | No | Port (default `8000`). |
| `JWT_SECRET` | For OAuth tokens only | Secret used to sign JWTs from `POST /oauth/token`. |

Optional: use a `.env` file in the working directory; `server.py` loads it via `python-dotenv`.

## Authentication

1. **API key (simplest)**  
   Send `X-API-Key: <your Asterwise API key>` on MCP HTTP requests.

2. **Bearer JWT**  
   `POST /oauth/token` with JSON:
   `{"grant_type":"client_credentials","client_id":"<api_key>","client_secret":"<api_key>"}`  
   Use `Authorization: Bearer <access_token>` on MCP requests. Requires `JWT_SECRET` on the server.

The server never persists keys; it forwards them to Asterwise as `X-API-Key`.

## Run locally

```bash
export ASTERWISE_API_BASE_URL=https://api.asterwise.com
export JWT_SECRET=your-long-random-secret   # optional, for /oauth/token
python server.py
```

Health check:

```bash
curl http://localhost:8000/health
```

MCP endpoint (FastMCP default): `/mcp/` (see [FastMCP HTTP deployment](https://gofastmcp.com/v2/deployment/http)).

## Docker

```bash
docker build -t asterwise-mcp .
docker run -e ASTERWISE_API_BASE_URL=https://api.asterwise.com -e JWT_SECRET=changeme -p 8000:8000 asterwise-mcp
```

## Deploy (Railway)

`railway.toml` uses the Dockerfile, health check path `/health`, and `python server.py` as the start command.

## Development

Dependencies are listed in `requirements.txt`. Install with:

```bash
pip install -r requirements.txt
```

Verify imports:

```bash
python -c "import server"
```
