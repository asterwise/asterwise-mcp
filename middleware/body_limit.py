"""Request body limits for the MCP server, enforced before anything reads it.

The auth wrapper drains POST /mcp bodies to inspect the JSON-RPC messages,
and the OAuth routes call ``request.json()``; without a limit a client
streaming gigabytes made the process buffer all of it. This pure ASGI layer
sits inside CORS and security headers (so a refusal still carries them) and
outside everything that reads bodies. It:

* refuses a declared ``Content-Length`` over the limit without reading;
* reads at most MAX_BODY_BYTES and refuses as soon as a body goes over,
  whatever the transfer encoding;
* gives the whole body BODY_READ_TIMEOUT_SECONDS to arrive;
* replays the buffered body to the app, then passes later messages
  (``http.disconnect``) through, so streaming responses still see the
  client leave.
"""

from __future__ import annotations

import asyncio

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# MCP JSON-RPC messages and OAuth forms are a few KB; this leaves room.
MAX_BODY_BYTES = 256 * 1024
BODY_READ_TIMEOUT_SECONDS = 30.0


class _TooLarge(Exception):
    pass


class _ClientGone(Exception):
    pass


class BodyLimitASGIWrapper:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return

        declared = _declared_length(scope)
        if declared is not None and declared > MAX_BODY_BYTES:
            await _refuse(scope, receive, send, 413, "payload_too_large",
                          f"Request body is larger than {MAX_BODY_BYTES // 1024} KB.")
            return
        try:
            async with asyncio.timeout(BODY_READ_TIMEOUT_SECONDS):
                body = await _read_body(receive)
        except _TooLarge:
            await _refuse(scope, receive, send, 413, "payload_too_large",
                          f"Request body is larger than {MAX_BODY_BYTES // 1024} KB.")
            return
        except _ClientGone:
            return
        except TimeoutError:
            await _refuse(scope, receive, send, 408, "request_timeout",
                          f"The request body did not arrive within {int(BODY_READ_TIMEOUT_SECONDS)} seconds.")
            return

        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


def _declared_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers") or []:
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            raise _ClientGone
        chunk = message.get("body", b"")
        total += len(chunk)
        if total > MAX_BODY_BYTES:
            raise _TooLarge
        chunks.append(chunk)
        if not message.get("more_body", False):
            return b"".join(chunks)


async def _refuse(scope: Scope, receive: Receive, send: Send, status: int, error: str, description: str) -> None:
    response = JSONResponse(
        {"error": error, "error_description": description},
        status_code=status,
        headers={"Connection": "close"},
    )
    await response(scope, receive, send)
