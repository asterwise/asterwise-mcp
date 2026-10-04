"""Bounded request bodies: nothing in the MCP server buffers more than
MAX_BODY_BYTES of one request, however the client sends it."""
from __future__ import annotations

import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient

from middleware import body_limit
from server import app


def _scope(headers=None, method="POST"):
    return {"type": "http", "method": method, "path": "/mcp", "headers": headers or []}


async def _run(chunks, *, headers=None, delay=0.0):
    read = 0
    app_saw: list[bytes] = []

    async def receive():
        nonlocal read
        if read < len(chunks):
            if delay:
                await asyncio.sleep(delay)
            chunk = chunks[read]
            read += 1
            return {"type": "http.request", "body": chunk, "more_body": read < len(chunks)}
        await asyncio.sleep(3600)

    sent = []

    async def send(message):
        sent.append(message)

    async def inner(scope, receive, send):
        app_saw.append((await receive())["body"])
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    await body_limit.BodyLimitASGIWrapper(inner)(_scope(headers), receive, send)
    status = next((m["status"] for m in sent if m["type"] == "http.response.start"), None)
    payload = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return status, payload, read, app_saw


async def test_streamed_oversize_body_stops_at_the_limit():
    status, payload, read, app_saw = await _run([b"a" * 65536] * 100)
    assert status == 413
    assert json.loads(payload)["error"] == "payload_too_large"
    assert read == 5  # 256 KB + one chunk, then it stops reading
    assert app_saw == []


async def test_declared_oversize_is_refused_without_reading():
    status, _p, read, app_saw = await _run([b"x"], headers=[(b"content-length", b"10000000")])
    assert status == 413 and read == 0 and app_saw == []


async def test_body_in_pieces_reaches_the_app_whole():
    status, payload, _r, app_saw = await _run([b'{"a"', b":1}"])
    assert (status, payload, app_saw) == (200, b"ok", [b'{"a":1}'])


async def test_slow_upload_is_cut_off(monkeypatch):
    monkeypatch.setattr(body_limit, "BODY_READ_TIMEOUT_SECONDS", 0.1)
    status, payload, _r, app_saw = await _run([b"a"] * 10, delay=0.05)
    assert status == 408
    assert json.loads(payload)["error"] == "request_timeout"
    assert app_saw == []


async def test_get_requests_pass_straight_through():
    called = []

    async def inner(scope, receive, send):
        called.append(scope["method"])

    async def never():
        raise AssertionError("GET bodies are not read")

    await body_limit.BodyLimitASGIWrapper(inner)(_scope(method="GET"), never, None)
    assert called == ["GET"]


async def test_the_server_refuses_a_huge_mcp_post_with_its_usual_headers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/mcp", content=b"[" + b" " * 400_000 + b"]",
                         headers={"Content-Type": "application/json", "Origin": "https://claude.ai"})
    assert r.status_code == 413
    assert r.json()["error"] == "payload_too_large"
    assert r.headers.get("access-control-allow-origin") == "*"
    assert r.headers.get("x-content-type-options") == "nosniff"
