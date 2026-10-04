"""The caller's address travels to the API, signed, on every upstream call.

Every request this server makes to the API leaves from one egress address,
so without this the API's per-IP limits would put every MCP user in the
same bucket. The signature is what stops a third party from choosing its
own bucket by sending the header directly to the API.
"""

from __future__ import annotations

import hashlib
import hmac
from contextvars import copy_context

import pytest

from auth import (
    CLIENT_IP_HEADER,
    CLIENT_IP_SIGNATURE_HEADER,
    forwarded_client_ip_headers,
    sign_client_ip,
)
from context import get_request_client_ip, set_request_client_ip


# ---- ContextVar ------------------------------------------------------------

def test_client_ip_contextvar_roundtrip() -> None:
    set_request_client_ip("203.0.113.9")
    try:
        assert get_request_client_ip() == "203.0.113.9"
    finally:
        set_request_client_ip(None)


def test_client_ip_contextvar_default_is_none() -> None:
    assert copy_context().run(get_request_client_ip) is None


# ---- Signature -------------------------------------------------------------

def test_signature_is_hmac_sha256_over_the_address() -> None:
    """Pinned to the primitive so the API side can verify it independently."""
    expected = hmac.new(b"shared-secret", b"203.0.113.9", hashlib.sha256).hexdigest()
    assert sign_client_ip("203.0.113.9", "shared-secret") == expected


def test_headers_carry_address_and_matching_signature(monkeypatch) -> None:
    monkeypatch.setenv("INTERNAL_API_TOKEN", "shared-secret")
    headers = forwarded_client_ip_headers("203.0.113.9")
    assert headers[CLIENT_IP_HEADER] == "203.0.113.9"
    assert headers[CLIENT_IP_SIGNATURE_HEADER] == sign_client_ip("203.0.113.9", "shared-secret")


@pytest.mark.parametrize("ip", [None, "", "unknown"])
def test_no_address_means_no_headers(monkeypatch, ip) -> None:
    monkeypatch.setenv("INTERNAL_API_TOKEN", "shared-secret")
    assert forwarded_client_ip_headers(ip) == {}


def test_no_shared_secret_means_no_headers(monkeypatch) -> None:
    """Without the secret the API could not verify the address, so do not
    send one it would have to ignore."""
    monkeypatch.delenv("INTERNAL_API_TOKEN", raising=False)
    assert forwarded_client_ip_headers("203.0.113.9") == {}


# ---- Middleware records the caller -----------------------------------------

@pytest.mark.asyncio
async def test_asgi_wrapper_records_the_callers_address() -> None:
    from server import APIKeyASGIWrapper

    seen: dict[str, str | None] = {}

    async def downstream(scope, receive, send):
        seen["ip"] = get_request_client_ip()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    app = APIKeyASGIWrapper(downstream)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [(b"x-api-key", b"aw_test_key_for_forwarding_1234567890")],
        "client": ("203.0.113.9", 51234),
        "query_string": b"",
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_msg):
        pass

    await app(scope, receive, send)
    assert seen["ip"] == "203.0.113.9"
    # Cleared after the request so nothing leaks into the next task.
    assert get_request_client_ip() is None


@pytest.mark.asyncio
async def test_tool_client_attaches_the_signed_address(monkeypatch) -> None:
    """The shared upstream client adds the headers from the ContextVar."""
    import client as client_mod

    monkeypatch.setenv("INTERNAL_API_TOKEN", "shared-secret")
    captured: dict[str, dict] = {}

    class _Resp:
        status_code = 200
        is_success = True
        headers = {"content-type": "application/json"}
        request = None

        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

        @property
        def content(self):
            return b'{"ok": true}'

        @property
        def text(self):
            return '{"ok": true}'

    class _Http:
        async def request(self, method, path, headers=None, timeout=None, **kwargs):
            captured["headers"] = dict(headers or {})
            return _Resp()

    c = client_mod.AsterwiseClient() if hasattr(client_mod, "AsterwiseClient") else None
    if c is None:  # locate the client class generically
        cls = next(v for k, v in vars(client_mod).items() if isinstance(v, type) and hasattr(v, "_request_with_retry"))
        c = cls()
    monkeypatch.setattr(c, "_client", lambda: _Http())

    set_request_client_ip("203.0.113.9")
    try:
        await c._request_with_retry("GET", "/v1/ping", "aw_key", timeout=5.0)
    finally:
        set_request_client_ip(None)

    h = captured["headers"]
    assert h[CLIENT_IP_HEADER] == "203.0.113.9"
    assert h[CLIENT_IP_SIGNATURE_HEADER] == sign_client_ip("203.0.113.9", "shared-secret")
    assert h["Authorization"] == "Bearer aw_key"


async def test_asgi_wrapper_records_the_visitor_behind_cloudflare() -> None:
    from server import APIKeyASGIWrapper

    seen: dict[str, str | None] = {}

    async def downstream(scope, receive, send):
        seen["ip"] = get_request_client_ip()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [(b"x-api-key", b"aw_test_key_for_forwarding_1234567890"),
                    (b"cf-connecting-ip", b"203.0.113.9")],
        "client": ("172.69.4.10", 51234),  # a Cloudflare edge
        "query_string": b"",
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_msg):
        pass

    await APIKeyASGIWrapper(downstream)(scope, receive, send)
    assert seen["ip"] == "203.0.113.9"
