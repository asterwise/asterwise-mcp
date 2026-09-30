"""Sentry for the MCP server.

Reports into the same Sentry project as asterwise-api, tagged
``component:mcp``; the httpx integration propagates the trace to the API, so
a tool call and the API request it made sit in one trace.

What is sent:
- Tool crashes (unexpected exceptions) and upstream API failures that
  survived the retries (5xx, timeouts, connection errors), once each, tagged
  with the tool, the MCP client (Claude, Cursor, ...), the upstream status
  and the API's request id.
- 20% of /mcp and OAuth transactions; health checks, discovery documents,
  OPTIONS and HEAD are not traced.

What is never sent:
- Request bodies: JSON-RPC bodies carry the tool arguments, which are birth
  data (max_request_body_size="never").
- Frame locals, extras and breadcrumb data under SCRUB_DENYLIST keys.
- Authorization / X-API-Key headers and cookies (send_default_pii=False).
- Client input errors (4xx from the API, invalid parameters).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("asterwise_mcp.observability")

# Stdout-only logger for lines that sit next to an explicit capture.
HANDLED_LOGGER_NAME = "asterwise_mcp.handled"

SCRUB_DENYLIST: list[str] = [
    "password", "passwd", "secret", "api_key", "apikey", "auth", "credentials",
    "token", "session", "cookie", "authorization", "x_api_key",
    "access_token", "refresh_token", "client_secret", "code_verifier", "code",
    "email", "name", "full_name", "phone", "mobile", "vehicle_number", "business_name",
    "birth", "birth_data", "date", "time", "datetime", "dob", "place", "city",
    "location", "latitude", "longitude", "lat", "lon", "lng", "birth_lat", "birth_lon",
    "person1", "person2", "partner", "boy", "girl", "arguments", "params", "body", "json",
]

_UNTRACED_PREFIXES = ("/health", "/.well-known/", "/robots.txt", "/favicon.ico", "/server-card")
TRACES_SAMPLE_RATE = 0.2

_enabled = False


def sentry_enabled() -> bool:
    return _enabled


def traces_sampler(ctx: dict[str, Any]) -> float:
    parent = ctx.get("parent_sampled")
    if parent is not None:
        return float(parent)
    scope = ctx.get("asgi_scope") or {}
    path = scope.get("path", "") if isinstance(scope, dict) else ""
    method = scope.get("method") if isinstance(scope, dict) else None
    if method in ("OPTIONS", "HEAD") or path.startswith(_UNTRACED_PREFIXES):
        return 0.0
    return TRACES_SAMPLE_RATE


def init_sentry() -> bool:
    """Initialise Sentry when SENTRY_DSN is set. Safe to call more than once."""
    global _enabled
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn or _enabled:
        return _enabled

    import sentry_sdk
    from sentry_sdk.integrations.logging import ignore_logger
    from sentry_sdk.integrations.starlette import StarletteIntegration
    from sentry_sdk.scrubber import EventScrubber

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        release=os.getenv("RAILWAY_GIT_COMMIT_SHA") or None,
        integrations=[
            # Tool errors are reported explicitly with tags; nothing here
            # raises HTTPException(5xx) that the SDK should capture itself.
            StarletteIntegration(failed_request_status_codes=set()),
        ],
        send_default_pii=False,
        max_request_body_size="never",
        event_scrubber=EventScrubber(denylist=SCRUB_DENYLIST, recursive=True),
        traces_sampler=traces_sampler,
        max_breadcrumbs=50,
    )
    sentry_sdk.set_tag("component", "mcp")
    ignore_logger(HANDLED_LOGGER_NAME)
    _enabled = True
    return True


def wrap_asgi(app: Any) -> Any:
    """Outermost ASGI wrapper: one isolation scope and transaction per request.

    The served app is a plain ASGI composition (CORS -> security headers ->
    auth -> dispatch), which the Starlette integration does not wrap.
    """
    if not _enabled:
        return app
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

    # "url": the default names each transaction after an endpoint that plain
    # ASGI apps do not have ("<unlabeled transaction>").
    return SentryAsgiMiddleware(app, transaction_style="url")


def tag_request(**tags: Any) -> None:
    """Tags on the current request's scope (inherited by tool captures)."""
    if not _enabled:
        return
    import sentry_sdk

    for key, value in tags.items():
        if value is not None:
            sentry_sdk.set_tag(key, str(value)[:200])


def capture_tool_failure(tool: str, exc: BaseException, **tags: Any) -> None:
    """One Sentry event for a tool call that failed on our side."""
    if not _enabled:
        return
    import sentry_sdk

    with sentry_sdk.new_scope() as scope:
        scope.set_tag("tool", tool)
        for key, value in tags.items():
            if value is not None:
                scope.set_tag(key, str(value)[:200])
        status = tags.get("upstream_status")
        # Upstream failures group by tool and status; crashes by stack trace.
        if status is not None or tags.get("failure") == "upstream":
            scope.fingerprint = ["mcp-upstream", tool, str(status or type(exc).__name__)]
        sentry_sdk.capture_exception(exc)
