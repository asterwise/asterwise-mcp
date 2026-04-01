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
