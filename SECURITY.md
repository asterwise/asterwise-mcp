# Security

This repository contains the Asterwise MCP server: a hosted proxy that
exposes the Asterwise astrology API (api.asterwise.com) as Model Context
Protocol tools at mcp.asterwise.com. It holds no secrets; every credential is
read from the environment at runtime.

## Reporting a vulnerability

Email **asterwiselabs@gmail.com** with the subject line `Security: <short
summary>`. Include steps to reproduce and the impact you believe it has. You
will get an acknowledgement within 2 business days and a status update within
7 days. Please give us a reasonable window to fix the issue before disclosing
it publicly.

In scope: this server (mcp.asterwise.com), the Asterwise API
(api.asterwise.com), and asterwise.com. Out of scope: denial-of-service
testing, rate-limit exhaustion, and automated scanning that degrades service
for other users; social engineering; third-party services we use.

## What is public by design

- Tool names, descriptions and input schemas (served to every MCP client).
- OAuth discovery documents under `/.well-known/`.
- The maintainer contact in `/.well-known/glama.json`.

## Supported versions

Only the deployed `main` branch is supported; there are no maintained
release branches.
