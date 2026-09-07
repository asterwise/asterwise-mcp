"""Run the Asterwise MCP server over stdio.

Use this entry point for hosts that speak stdio rather than HTTP: Glama's
hosted builds (which wrap the command in mcp-proxy), Claude Desktop's local
server config, or a quick local test.

    ASTERWISE_API_KEY=aw_... python stdio.py

Over stdio there are no per-request HTTP headers, so the API key comes from
the ASTERWISE_API_KEY environment variable. The server starts and lists its
tools without a key; tool calls need one. Logs go to stderr so stdout stays
a clean MCP channel.
"""

from __future__ import annotations

import os

# Hosted builds usually set nothing; the public API is the sensible default.
os.environ.setdefault("ASTERWISE_API_BASE_URL", "https://api.asterwise.com")

from server import mcp  # noqa: E402  (importing configures stderr logging)


def main() -> None:
    try:
        mcp.run(transport="stdio", show_banner=False)
    except TypeError:  # older FastMCP without show_banner
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
