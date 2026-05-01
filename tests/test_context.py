"""ContextVar API key storage (middleware → tools)."""

from __future__ import annotations

from contextvars import copy_context

from context import get_request_api_key, set_request_api_key


def test_contextvar_roundtrip() -> None:
    set_request_api_key("test-key-123")
    try:
        assert get_request_api_key() == "test-key-123"
    finally:
        set_request_api_key(None)


def test_contextvar_default_is_none() -> None:
    def check() -> str | None:
        return get_request_api_key()

    ctx = copy_context()
    result = ctx.run(check)
    assert result is None
