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


def _initialize(client_name):
    return _rpc(
        "initialize",
        params={"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": client_name, "version": "1"}},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("client_name", ["cursor-vscode", "Cursor", " CURSOR "])
async def test_cursor_initialize_gets_oauth_challenge(client_name):
    # Cursor only starts OAuth when initialize itself is refused.
    rec = _Recorder()
    app = srv.APIKeyASGIWrapper(rec)
    status, headers = await _run(app, _scope(), _initialize(client_name))
    assert status == 401
    assert "resource_metadata" in headers.get("www-authenticate", "")
    assert not rec.called


@pytest.mark.asyncio
async def test_cursor_initialize_with_token_passes():
    rec = _Recorder()
    app = srv.APIKeyASGIWrapper(rec)
    body = _initialize("cursor-vscode")
    status, _ = await _run(app, _scope(headers={"X-API-Key": "aw_test_key"}), body)
    assert status == 200 and rec.called and rec.body == body


@pytest.mark.asyncio
@pytest.mark.parametrize("client_name", ["claude-ai", "openai-mcp", "glama", "cursor-like", ""])
async def test_other_clients_keep_anonymous_initialize(client_name):
    rec = _Recorder()
    app = srv.APIKeyASGIWrapper(rec)
    status, _ = await _run(app, _scope(), _initialize(client_name))
    assert status == 200 and rec.called


def test_oauth_on_initialize_predicate_edge_cases():
    assert not srv._public_mcp_methods_only(
        json.dumps([json.loads(_initialize("cursor-vscode")), json.loads(_rpc("tools/list"))]).encode()
    )
    assert srv._public_mcp_methods_only(_rpc("initialize", params={"clientInfo": "cursor"}))
    assert srv._public_mcp_methods_only(_rpc("initialize", params={"clientInfo": {"name": 5}}))
    assert srv._public_mcp_methods_only(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": []}).encode())
    # Only initialize is gated; a later anonymous tools/list is unaffected.
    assert srv._public_mcp_methods_only(_rpc("tools/list", params={"clientInfo": {"name": "cursor"}}))


class _SessionApp(_Recorder):
    """Recorder that answers like the MCP app, with a session id header."""

    def __init__(self, session_id="sess-1"):
        super().__init__()
        self.session_id = session_id

    async def __call__(self, scope, receive, send):
        self.called = True
        while True:
            m = await receive()
            if not m.get("more_body", False):
                break
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json"), (b"mcp-session-id", self.session_id.encode())],
        })
        await send({"type": "http.response.body", "body": b"{}", "more_body": False})


def _records(caplog, message):
    return [r for r in caplog.records if r.getMessage() == message]


@pytest.mark.asyncio
async def test_initialize_logs_client_and_outcome(caplog):
    caplog.set_level("INFO", logger="asterwise_mcp.server")
    app = srv.APIKeyASGIWrapper(_SessionApp("sess-log-1"))
    await _run(app, _scope(headers={"User-Agent": "Glama/1"}), _initialize("glama-check"))
    (rec,) = _records(caplog, "mcp_client_initialize")
    assert rec.client_name == "glama-check" and rec.client_version == "1"
    assert rec.protocol_version == "2025-06-18"
    assert rec.authenticated is False and rec.status == 200 and rec.user_agent == "Glama/1"
    assert srv._MCP_SESSION_CLIENTS["sess-log-1"]["client_name"] == "glama-check"


@pytest.mark.asyncio
async def test_authenticated_initialize_logged_and_body_replayed(caplog):
    caplog.set_level("INFO", logger="asterwise_mcp.server")
    rec_app = _Recorder()
    app = srv.APIKeyASGIWrapper(rec_app)
    body = _initialize("cursor-vscode")
    status, _ = await _run(app, _scope(headers={"X-API-Key": "aw_test_key"}), body, chunks=2)
    assert status == 200 and rec_app.body == body
    (rec,) = _records(caplog, "mcp_client_initialize")
    assert rec.client_name == "cursor-vscode" and rec.authenticated is True


@pytest.mark.asyncio
async def test_anonymous_tools_call_challenge_attributed_to_session_client(caplog):
    caplog.set_level("INFO", logger="asterwise_mcp.server")
    await _run(srv.APIKeyASGIWrapper(_SessionApp("sess-log-2")), _scope(), _initialize("some-ide"))
    caplog.clear()
    rec_app = _Recorder()
    body = _rpc("tools/call", params={"name": "asterwise_get_natal_chart", "arguments": {}})
    status, _ = await _run(srv.APIKeyASGIWrapper(rec_app), _scope(headers={"Mcp-Session-Id": "sess-log-2"}), body)
    assert status == 401 and not rec_app.called
    (rec,) = _records(caplog, "mcp_auth_challenge")
    assert rec.client_name == "some-ide" and rec.session_client_known is True
    assert rec.rpc_methods == ["tools/call"] and rec.http_method == "POST"


@pytest.mark.asyncio
async def test_cursor_initialize_challenge_logged(caplog):
    caplog.set_level("INFO", logger="asterwise_mcp.server")
    await _run(srv.APIKeyASGIWrapper(_Recorder()), _scope(), _initialize("cursor-vscode"))
    (challenge,) = _records(caplog, "mcp_auth_challenge")
    assert challenge.client_name == "cursor-vscode" and challenge.rpc_methods == ["initialize"]
    (init,) = _records(caplog, "mcp_client_initialize")
    assert init.status == 401 and init.authenticated is False


@pytest.mark.asyncio
async def test_unknown_session_get_challenge_logged_without_client(caplog):
    caplog.set_level("INFO", logger="asterwise_mcp.server")
    await _run(srv.APIKeyASGIWrapper(_Recorder()), _scope(method="GET", headers={"Mcp-Session-Id": "nope"}), b"")
    (rec,) = _records(caplog, "mcp_auth_challenge")
    assert rec.client_name is None and rec.session_client_known is False
    assert rec.http_method == "GET" and rec.has_session is True and rec.rpc_methods == []


def test_session_client_map_is_bounded(monkeypatch):
    monkeypatch.setattr(srv, "_MCP_SESSION_CLIENTS_MAX", 3)
    monkeypatch.setattr(srv, "_MCP_SESSION_CLIENTS", srv.OrderedDict())
    for i in range(5):
        srv._remember_session_client(f"s{i}", {"client_name": str(i)})
    assert list(srv._MCP_SESSION_CLIENTS) == ["s2", "s3", "s4"]


def test_initialize_client_tolerates_odd_shapes():
    assert srv._initialize_client([{"method": "initialize", "params": "x"}]) == {
        "client_name": None, "client_version": None, "protocol_version": None,
    }
    assert srv._initialize_client([{"method": "tools/list"}]) is None
    long = srv._initialize_client([{"method": "initialize", "params": {"clientInfo": {"name": "n" * 500}}}])
    assert len(long["client_name"]) == 100
