"""Lazy authentication on /mcp: public methods pass without credentials,
everything else still gets the OAuth 401 challenge."""

import json

import pytest

import server as srv


class _Recorder:
    """Minimal ASGI app that records whether it ran and what body it read."""

    def __init__(self) -> None:
        self.called = False
        self.body = b""

    async def __call__(self, scope, receive, send):
        self.called = True
        chunks = []
        while True:
            m = await receive()
            chunks.append(m.get("body", b""))
            if not m.get("more_body", False):
                break
        self.body = b"".join(chunks)
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b'{"ok":true}', "more_body": False})


def _scope(method="POST", path="/mcp", headers=None):
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "query_string": b"",
    }


async def _run(app, scope, body: bytes, chunks: int = 1):
    parts = [body] if chunks == 1 else [body[: len(body) // 2], body[len(body) // 2 :]]
    queue = [
        {"type": "http.request", "body": p, "more_body": i < len(parts) - 1}
        for i, p in enumerate(parts)
    ]
    sent = []

    async def receive():
        return queue.pop(0) if queue else {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    headers = {k.decode().lower(): v.decode() for k, v in next(m for m in sent if m["type"] == "http.response.start")["headers"]}
    return status, headers


def _rpc(method, id_=1, params=None):
    return json.dumps({"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}).encode()


@pytest.mark.asyncio
@pytest.mark.parametrize("method", sorted(srv.PUBLIC_MCP_METHODS))
async def test_public_methods_pass_without_credentials(method):
    rec = _Recorder()
    app = srv.APIKeyASGIWrapper(rec)
    body = _rpc(method)
    status, _ = await _run(app, _scope(), body)
    assert status == 200
    assert rec.called
    assert rec.body == body  # body replayed intact to the MCP app


@pytest.mark.asyncio
async def test_public_method_body_replayed_across_chunks():
    rec = _Recorder()
    app = srv.APIKeyASGIWrapper(rec)
    body = _rpc("tools/list")
    status, _ = await _run(app, _scope(), body, chunks=2)
    assert status == 200 and rec.body == body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        _rpc("tools/call", params={"name": "asterwise_get_natal_chart", "arguments": {}}),
        json.dumps([json.loads(_rpc("tools/list")), json.loads(_rpc("tools/call"))]).encode(),
        b"{not json",
        b"",
        b"[]",
        b'{"jsonrpc":"2.0","id":1}',
        b'{"jsonrpc":"2.0","id":1,"method":5}',
        b"[1,2]",
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "resources/read", "params": {"uri": "x"}}).encode(),
        b'{"jsonrpc":"2.0","id":1,"method":"tools/list","pad":"' + b"x" * (srv._PUBLIC_MCP_BODY_LIMIT + 10) + b'"}',
    ],
)
async def test_non_public_or_malformed_requests_still_get_401(body):
    rec = _Recorder()
    app = srv.APIKeyASGIWrapper(rec)
    status, headers = await _run(app, _scope(), body)
    assert status == 401
    assert "resource_metadata" in headers.get("www-authenticate", "")
    assert not rec.called


@pytest.mark.asyncio
async def test_get_mcp_without_credentials_still_401():
    rec = _Recorder()
    app = srv.APIKeyASGIWrapper(rec)
    status, headers = await _run(app, _scope(method="GET"), b"")
    assert status == 401 and not rec.called


@pytest.mark.asyncio
async def test_other_paths_unaffected():
    rec = _Recorder()
    app = srv.APIKeyASGIWrapper(rec)
    status, _ = await _run(app, _scope(path="/something"), _rpc("tools/list"))
    assert status == 401 and not rec.called


@pytest.mark.asyncio
async def test_tools_call_with_api_key_passes():
    rec = _Recorder()
    app = srv.APIKeyASGIWrapper(rec)
    body = _rpc("tools/call", params={"name": "x", "arguments": {}})
    status, _ = await _run(app, _scope(headers={"X-API-Key": "aw_test_key"}), body)
    assert status == 200 and rec.called and rec.body == body


def test_public_method_predicate_edge_cases():
    assert srv._public_mcp_methods_only(_rpc("initialize"))
    assert srv._public_mcp_methods_only(json.dumps([json.loads(_rpc("initialize")), json.loads(_rpc("tools/list"))]).encode())
    assert not srv._public_mcp_methods_only(b"null")
    assert not srv._public_mcp_methods_only(b'"tools/list"')
    assert not srv._public_mcp_methods_only(_rpc("tools/list ").replace(b"tools/list ", b"tools/lis"))
