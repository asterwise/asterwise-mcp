"""
Safety net over every registered tool.

For each of the 103 tools this builds a valid argument set from the tool's
own input schema, invokes it through an in-process FastMCP client with the
upstream HTTP client replaced by a fake, and asserts the contract every tool
shares:

  * a successful upstream call yields text content and exactly one upstream
    request under /v1/
  * an upstream AsterwiseMCPError surfaces to the client as an error carrying
    the upstream message (not a stack trace)
  * an unexpected exception surfaces as the generic "Unexpected error in
    <tool>" message
  * without an API key the tool refuses before calling upstream

The argument heuristics live in _example_for(); extend them if a new tool
introduces a field they cannot satisfy (the failure message names the tool
and the validation error).
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

import client as client_mod
from context import set_request_api_key
from errors import AsterwiseMCPError
from fastmcp import Client
from server import mcp

_PLACEHOLDER = {
    "date": "1990-06-15", "birth_date": "1990-06-15", "from_date": "2026-01-01",
    "to_date": "2026-01-31", "start_date": "2026-01-01", "end_date": "2026-01-31",
    "target_date": "2026-03-01", "transit_date": "2026-03-01", "query_date": "2026-03-01",
    "time": "14:30", "birth_time": "14:30", "timezone": "Asia/Kolkata", "tz": "Asia/Kolkata",
    "latitude": 19.076, "lat": 19.076, "longitude": 72.8777, "lon": 72.8777, "lng": 72.8777,
    "name": "Test Person", "full_name": "Test Person", "person1_name": "Person One",
    "person2_name": "Person Two", "person1_date": "1990-06-15", "person2_date": "1992-02-20",
    "business_name": "Asterwise Labs", "nakshatra_name": "Ashwini", "planet": "Sun",
    "sign": "Aries", "moon_sign": "aries", "sun_sign": "aries", "zodiac_sign": "aries",
    "mobile_number": "9876543210", "vehicle_number": "MH12AB1234", "number": 7,
    "angel_number": "111", "year": 2026, "target_year": 2026, "month": 3, "day": 15,
    "activity": "marriage", "location": "Mumbai, India", "city": "Mumbai",
    "prashna": "Will the project succeed?", "question": "Will the project succeed?",
    "symbol": "snake", "slug": "snake", "card": "the-fool", "card_name": "The Fool",
    "suit": "cups", "category": "animals", "crystal": "amethyst", "crystal_name": "amethyst",
    "chart_type": "D9", "dasha_type": "vimshottari", "system": "pythagorean",
    "ayanamsa": "lahiri", "house_system": "placidus", "gender": "male",
    "period": "daily", "horizon": "daily", "count": 3, "days": 7, "limit": 5,
    "age": 30, "age_years": 30, "return_number": 1, "birth_year": 1990,
}


def _example_for(prop_name: str, schema: dict[str, Any]) -> Any:
    """Pick a plausible value for one property from its JSON schema."""
    if "enum" in schema:
        return schema["enum"][0]
    for branch in schema.get("anyOf", []):
        if branch.get("type") != "null":
            return _example_for(prop_name, branch)
    if "const" in schema:
        return schema["const"]
    typ = schema.get("type")
    if prop_name == "positions" and "properties" not in schema:
        # Free-form {body: longitude} map (western aspects) needs two bodies.
        return {"Sun": 10.0, "Moon": 100.0}
    if typ == "object" or "properties" in schema:
        return _example_object(schema)
    if typ == "array":
        item = _example_for(prop_name, schema.get("items", {"type": "string"}))
        return [item] * max(1, int(schema.get("minItems", 1)))
    if prop_name in _PLACEHOLDER:
        val = _PLACEHOLDER[prop_name]
        if typ == "string":
            return str(val)
        if typ == "integer":
            return int(val) if not isinstance(val, str) else 7
        if typ == "number":
            return float(val) if not isinstance(val, str) else 1.0
        return val
    if typ == "integer":
        return int(schema.get("minimum", 1))
    if typ == "number":
        return float(schema.get("minimum", 1.0))
    if typ == "boolean":
        return True
    lname = prop_name.lower()
    if "date" in lname:
        return "1990-06-15"
    if "time" in lname:
        return "14:30"
    if "zone" in lname:
        return "Asia/Kolkata"
    if "lat" in lname:
        return 19.076
    if "lon" in lname or "lng" in lname:
        return 72.8777
    if "name" in lname:
        return "Test Person"
    return "example"


def _example_object(schema: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    props = schema.get("properties", {})
    for req in schema.get("required", []):
        out[req] = _example_for(req, props.get(req, {}))
    return out


class FakeUpstream:
    """Stands in for client.AsterwiseClient; records calls."""

    def __init__(self, behaviour: str = "ok") -> None:
        self.behaviour = behaviour
        self.calls: list[tuple[str, str]] = []

    # The app lifespan opens/closes the shared client; no-ops here.
    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def _respond(self, method: str, path: str) -> dict[str, Any]:
        self.calls.append((method, path))
        if self.behaviour == "upstream_error":
            raise AsterwiseMCPError("upstream boom: simulated failure")
        if self.behaviour == "crash":
            raise RuntimeError("simulated crash")
        return {
            "success": True,
            "data": {"result": "ok", "nested": {"value": 1, "items": [1, 2, 3]}},
            "request_id": "should-be-scrubbed",
        }

    async def get(self, path, api_key, params=None, *, timeout=10.0):
        return await self._respond("GET", path)

    async def post(self, path, api_key, body, *, timeout=20.0):
        return await self._respond("POST", path)


def _tool_specs() -> list[tuple[str, dict[str, Any]]]:
    async def _load():
        async with Client(mcp) as c:
            return [(t.name, t.inputSchema) for t in await c.list_tools()]
    return sorted(asyncio.run(_load()), key=lambda x: x[0])


TOOL_SPECS = _tool_specs()
TOOL_NAMES = [name for name, _ in TOOL_SPECS]


def test_registry_has_the_documented_tool_count():
    assert len(TOOL_SPECS) == 103


async def _call(name: str, args: dict[str, Any], upstream: FakeUpstream, *, with_key: bool = True):
    client_mod._client_singleton = upstream  # get_client() returns this
    set_request_api_key("aw_test_key_0123456789" if with_key else None)
    try:
        async with Client(mcp) as c:
            return await c.call_tool(name, args, raise_on_error=False)
    finally:
        set_request_api_key(None)
        client_mod._client_singleton = None


def _text(result) -> str:
    return "\n".join(getattr(block, "text", "") for block in (result.content or []))


@pytest.mark.parametrize("name,schema", TOOL_SPECS, ids=TOOL_NAMES)
def test_tool_success_path(name: str, schema: dict[str, Any]) -> None:
    args = _example_object(schema)
    upstream = FakeUpstream("ok")
    result = asyncio.run(_call(name, args, upstream))
    assert not result.is_error, f"{name} rejected generated args {json.dumps(args)}: {_text(result)}"
    body = _text(result)
    assert body.strip(), f"{name} returned empty content"
    # A few tools compose several upstream endpoints (e.g. special ascendants
    # calls atmakaraka and ishta-devta); every call must still be under /v1/.
    assert 1 <= len(upstream.calls) <= 3, f"{name} made {len(upstream.calls)} upstream calls"
    for _method, path in upstream.calls:
        assert path.startswith("/v1/"), f"{name} called {path}"
    assert "should-be-scrubbed" not in body, f"{name} leaked an internal field"


@pytest.mark.parametrize("name,schema", TOOL_SPECS, ids=TOOL_NAMES)
def test_tool_maps_upstream_error(name: str, schema: dict[str, Any]) -> None:
    result = asyncio.run(_call(name, _example_object(schema), FakeUpstream("upstream_error")))
    assert result.is_error, f"{name} did not surface the upstream error"
    assert "upstream boom" in _text(result), _text(result)


@pytest.mark.parametrize("name,schema", TOOL_SPECS, ids=TOOL_NAMES)
def test_tool_maps_unexpected_exception(name: str, schema: dict[str, Any]) -> None:
    result = asyncio.run(_call(name, _example_object(schema), FakeUpstream("crash")))
    assert result.is_error
    text = _text(result)
    assert f"Unexpected error in {name}" in text, text
    assert "simulated crash" not in text, "internal exception text leaked to the client"


@pytest.mark.parametrize("name,schema", TOOL_SPECS, ids=TOOL_NAMES)
def test_tool_requires_api_key(name: str, schema: dict[str, Any]) -> None:
    upstream = FakeUpstream("ok")
    result = asyncio.run(_call(name, _example_object(schema), upstream, with_key=False))
    assert result.is_error
    assert "No API key" in _text(result), _text(result)
    assert upstream.calls == [], f"{name} called upstream without an API key"
