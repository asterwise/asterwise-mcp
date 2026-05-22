"""SecurityHeadersASGIWrapper — applies canonical asterwise security
headers to every MCP server response.

Canonical set declared in asterwise-api/_docs/SECURITY_HEADERS.md.
"""
from __future__ import annotations

from typing import Callable

_PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), "
    "usb=(), magnetometer=(), accelerometer=(), gyroscope=(), "
    "browsing-topics=()"
)

_SECURITY_HEADERS = [
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"permissions-policy", _PERMISSIONS_POLICY.encode("ascii")),
]


class SecurityHeadersASGIWrapper:
    """ASGI wrapper that adds canonical security headers to every
    response.

    Headers applied:
    - Strict-Transport-Security: 1-year, includeSubDomains
    - X-Content-Type-Options: nosniff
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: deny camera, mic, geo, payment, USB,
      motion sensors, browsing-topics

    Not set:
    - X-Frame-Options: MCP returns JSON/SSE to programmatic clients.
      The /oauth/authorize flow may render in browser — if so,
      that route should add X-Frame-Options on its specific
      response, not globally.
    - Content-Security-Policy: JSON/SSE responses do not execute
      scripts.
    """

    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                existing = list(message.get("headers", []))
                # Add only if not already present (defensive against
                # downstream middleware setting the same header).
                existing_names = {h[0].lower() for h in existing}
                for name, value in _SECURITY_HEADERS:
                    if name not in existing_names:
                        existing.append((name, value))
                message["headers"] = existing
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
