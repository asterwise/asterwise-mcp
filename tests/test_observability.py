"""What the MCP server reports to Sentry, and what it tells the API."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import httpx
import pytest
import sentry_sdk
from mcp.shared.exceptions import McpError
from sentry_sdk.transport import Transport

import observability
import runtime
from client import AsterwiseClient
from errors import AsterwiseAPIError

# ---- upstream client -------------------------------------------------------


def _client_with(handler) -> AsterwiseClient:
    c = AsterwiseClient()
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.test")
    c._client = lambda: http  # type: ignore[method-assign]
    return c


@pytest.mark.asyncio
async def test_request_id_sent_upstream_and_carried_on_errors():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["rid"] = request.headers.get("X-Request-ID")
        return httpx.Response(
            500,
            json={"success": False, "error": "internal_error", "message": "boom",
                  "details": [], "request_id": "api-rid-123"},
            headers={"X-Request-ID": "api-rid-123"},
        )

    with pytest.raises(AsterwiseAPIError) as info:
        await _client_with(handler).post("/v1/astro/natal", "aw_key", {})
    assert uuid.UUID(seen["rid"])  # a full UUID the API accepts and tags
    assert info.value.status_code == 500
    assert info.value.api_request_id == "api-rid-123"


@pytest.mark.asyncio
async def test_api_envelope_validation_details_reach_the_model():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={
            "success": False, "error": "validation_error", "message": "Invalid request",
            "details": [{"loc": ["body", "birth", "date"], "msg": "invalid date"}],
            "request_id": "rid-422-abcdef",
        })

    with pytest.raises(AsterwiseAPIError) as info:
        await _client_with(handler).post("/v1/astro/natal", "aw_key", {})
    assert "invalid date" in str(info.value)
    assert info.value.status_code == 422


# ---- tool_guard reporting --------------------------------------------------


async def _run_guarded(exc: BaseException):
    calls = []
    with patch.object(runtime, "capture_tool_failure", lambda tool, e, **kw: calls.append((tool, e, kw))):
        with pytest.raises(McpError):
            async with runtime.tool_guard("asterwise_get_natal_chart"):
                raise exc
    return calls


@pytest.mark.asyncio
async def test_client_errors_are_not_reported():
    assert await _run_guarded(AsterwiseAPIError("bad input", status_code=422)) == []
    assert await _run_guarded(AsterwiseAPIError("rate limited", status_code=429)) == []


@pytest.mark.asyncio
async def test_upstream_5xx_reported_with_status_and_api_request_id():
    (call,) = await _run_guarded(AsterwiseAPIError("down", status_code=503, api_request_id="rid-503-abcdef"))
    tool, _, tags = call
    assert tool == "asterwise_get_natal_chart"
    assert tags == {"failure": "upstream", "upstream_status": 503, "api_request_id": "rid-503-abcdef"}


@pytest.mark.asyncio
async def test_crash_and_timeout_reported_once():
    (crash,) = await _run_guarded(RuntimeError("bug"))
    assert crash[2] == {"failure": "crash", "upstream_status": None}
    (timeout,) = await _run_guarded(httpx.ReadTimeout("slow"))
    assert timeout[2] == {"failure": "upstream", "upstream_status": "timeout"}


# ---- sampling --------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "method", "expected"),
    [
        ("/health", "GET", 0.0),
        ("/.well-known/oauth-protected-resource", "GET", 0.0),
        ("/mcp", "OPTIONS", 0.0),
        ("/mcp", "POST", observability.TRACES_SAMPLE_RATE),
    ],
)
def test_traces_sampler(path, method, expected):
    assert observability.traces_sampler({"asgi_scope": {"path": path, "method": method}}) == expected


# ---- the real SDK ----------------------------------------------------------


class _Capture(Transport):
    def __init__(self, options=None):
        super().__init__(options)
        self.events = []
        self.raw: list[str] = []

    def capture_envelope(self, envelope):
        self.events += [i.payload.json for i in envelope.items if i.type == "event"]
        self.raw.append(envelope.serialize().decode("utf-8", "replace"))


@pytest.fixture
def live_sentry(monkeypatch):
    transport = _Capture()
    real_init = sentry_sdk.init
    monkeypatch.setenv("SENTRY_DSN", "https://public@o0.ingest.sentry.io/0")
    monkeypatch.setattr(sentry_sdk, "init", lambda *a, **kw: real_init(*a, transport=transport, **kw))
    monkeypatch.setattr(observability, "_enabled", False)
    assert observability.init_sentry()
    yield transport
    real_init()
    monkeypatch.setattr(observability, "_enabled", False)


def test_tool_failure_event_is_tagged_and_scrubbed(live_sentry):
    def call_tool(birth, response_format):
        raise RuntimeError("engine failed")

    try:
        call_tool({"date": "1990-05-17", "latitude": 28.6}, "json")
    except RuntimeError as exc:
        observability.capture_tool_failure(
            "asterwise_get_natal_chart", exc, failure="crash", upstream_status=None,
        )
    sentry_sdk.flush()

    (event,) = live_sentry.events
    assert event["tags"]["tool"] == "asterwise_get_natal_chart"
    assert event["tags"]["component"] == "mcp"
    frames = event["exception"]["values"][0]["stacktrace"]["frames"]
    assert any(f.get("function") == "call_tool" for f in frames)
    # Frame variables are not sent at all: tool arguments sit in them under
    # any name. (Source context lines, i.e. this test's own literal, are code.)
    assert not any("vars" in f for f in frames)
    assert "request" not in event or not event["request"].get("data")


def test_upstream_failures_group_by_tool_and_status(live_sentry):
    for rid in ("rid-a-12345678", "rid-b-12345678"):
        observability.capture_tool_failure(
            "asterwise_get_dasha",
            AsterwiseAPIError(f"down {rid}", status_code=503, api_request_id=rid),
            failure="upstream", upstream_status=503, api_request_id=rid,
        )
    sentry_sdk.flush()

    fingerprints = {tuple(e["fingerprint"]) for e in live_sentry.events}
    assert fingerprints == {("mcp-upstream", "asterwise_get_dasha", "503")}
    assert {e["tags"]["api_request_id"] for e in live_sentry.events} == {"rid-a-12345678", "rid-b-12345678"}


def test_disabled_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.setattr(observability, "_enabled", False)
    assert observability.init_sentry() is False
    app = object()
    assert observability.wrap_asgi(app) is app
    observability.tag_request(mcp_client="cursor")  # no-op, no error


@pytest.mark.asyncio
async def test_upstream_call_query_never_reaches_sentry(live_sentry, monkeypatch):
    """GET tools put birth data and phone numbers in the API call's query
    string; the httpx integration records it on spans and breadcrumbs."""
    monkeypatch.setattr(observability, "TRACES_SAMPLE_RATE", 1.0)
    birth_date = "-".join(["1987", "06", "05"])
    phone = "98765" + "43210"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"success": False, "error": "internal_error",
                                         "message": "boom", "details": [], "request_id": "rid-x-12345678"})

    client = AsterwiseClient()
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.test")
    client._client = lambda: http  # type: ignore[method-assign]
    monkeypatch.setattr("client.BASE_DELAY", 0, raising=False)
    monkeypatch.setattr("client.MAX_DELAY", 0, raising=False)

    with sentry_sdk.start_transaction(name="tools/call", op="mcp.tool"):
        try:
            await client.get("/v1/numerology/life-path", "aw_key", params={"date": birth_date, "number": phone})
        except AsterwiseAPIError as exc:
            observability.capture_tool_failure("asterwise_get_life_path", exc, failure="upstream", upstream_status=500)
    sentry_sdk.flush()

    sent = "\n".join(live_sentry.raw)
    assert "life-path" in sent  # the call itself was recorded
    assert birth_date not in sent
    assert phone not in sent


def test_frame_variables_are_never_sent(live_sentry):
    assert sentry_sdk.get_client().options["include_local_variables"] is False
