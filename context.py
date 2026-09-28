"""ContextVar storage for per-request API key (set by HTTP middleware)."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

# Thread- and task-safe: set by Starlette middleware, read by tools in the same request.
_api_key_var: ContextVar[Optional[str]] = ContextVar("api_key", default=None)


def set_request_api_key(key: Optional[str]) -> None:
    """Called by middleware to store the resolved API key for this ASGI request."""
    _api_key_var.set(key)


def get_request_api_key() -> Optional[str]:
    """Return the API key for the current request, if middleware set one."""
    return _api_key_var.get()


# The caller's network address, captured by the same middleware. Forwarded to
# the API (signed) so its per-IP limits see the real user rather than this
# server's egress address for everyone.
_client_ip_var: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)


def set_request_client_ip(ip: Optional[str]) -> None:
    """Called by middleware to store the caller's address for this ASGI request."""
    _client_ip_var.set(ip)


def get_request_client_ip() -> Optional[str]:
    """Return the caller's address for the current request, if middleware set one."""
    return _client_ip_var.get()
