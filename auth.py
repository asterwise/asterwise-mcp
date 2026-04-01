"""Two-layer auth: X-API-Key and Bearer JWT (OAuth-style token exchange)."""

from __future__ import annotations

import os
import time
from typing import Any

import jwt
from starlette.requests import Request

from errors import AuthError, TokenExpiredError, TokenInvalidError

JWT_ALGORITHM = "HS256"
JWT_TTL_SECONDS = 3600


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise AuthError(
            "JWT_SECRET is not configured on the server. "
            "Set JWT_SECRET in the environment to use Bearer token auth, "
            "or use X-API-Key instead.",
            hint="Configure JWT_SECRET or pass X-API-Key.",
        )
    return secret


def extract_api_key(request: Request) -> str | None:
    """Try Bearer JWT first, then X-API-Key."""
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if not token:
            return None
        try:
            return decode_token(token)
        except TokenExpiredError:
            raise
        except TokenInvalidError:
            raise
    raw = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if raw and raw.strip():
        return raw.strip()
    return None


def validate_and_get_key(request: Request) -> str:
    """Return a valid API key or raise AuthError."""
    key = extract_api_key(request)
    if not key:
        raise AuthError(
            "Missing authentication. Provide "
            "`X-API-Key: <your Asterwise API key>` or "
            "`Authorization: Bearer <token>` from POST /oauth/token. "
            "Obtain a key at https://asterwise.com/dashboard.",
            hint="Add X-API-Key or Authorization Bearer.",
        )
    return key


def create_token(api_key: str) -> str:
    """Create a signed JWT containing the API key (1 hour TTL)."""
    now = int(time.time())
    payload: dict[str, Any] = {
        "api_key": api_key,
        "iat": now,
        "exp": now + JWT_TTL_SECONDS,
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> str:
    """Validate JWT and return the embedded API key."""
    try:
        payload = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError(
            "Bearer token expired. Request a new token from POST /oauth/token "
            "or use X-API-Key directly.",
            hint="Refresh OAuth token or use X-API-Key.",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError(
            "Invalid Bearer token. Use a token from POST /oauth/token with a valid API key, "
            "or pass X-API-Key instead.",
            hint="Obtain a fresh token or use X-API-Key.",
        ) from exc
    api_key = payload.get("api_key")
    if not isinstance(api_key, str) or not api_key.strip():
        raise TokenInvalidError(
            "Token payload missing api_key claim.",
            hint="Request a new token from POST /oauth/token.",
        )
    return api_key.strip()
