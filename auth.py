"""Two-layer auth: X-API-Key and Bearer JWT (OAuth-style token exchange)."""

from __future__ import annotations

import hashlib
import os
import time
from typing import Any

import jwt
from starlette.requests import Request

from errors import AuthError, TokenExpiredError, TokenInvalidError

JWT_ALGORITHM = "HS256"
JWT_TTL_SECONDS = 3600

# In-memory store: {key_hash: (api_key, expires_at)}
_key_cache: dict[str, tuple[str, float]] = {}


def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def _evict_expired_tokens() -> None:
    """Remove expired entries from cache."""
    now = time.time()
    expired = [h for h, (_, exp) in _key_cache.items() if now > exp]
    for h in expired:
        _key_cache.pop(h, None)


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
    """Create a signed JWT referencing the API key only via hash (cache holds the secret)."""
    key_hash = _hash_key(api_key)
    expires_at = time.time() + JWT_TTL_SECONDS
    _key_cache[key_hash] = (api_key, expires_at)
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": key_hash,
        "iat": now,
        "exp": int(expires_at),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> str:
    """Validate JWT and return the API key from the server cache."""
    try:
        payload = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
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

    key_hash = payload.get("sub")
    if not isinstance(key_hash, str) or not key_hash.strip():
        raise TokenInvalidError(
            "Invalid token structure.",
            hint="Request a new token from POST /oauth/token.",
        )

    cached = _key_cache.get(key_hash)
    if not cached:
        raise TokenInvalidError(
            "Token not recognized. Please re-authenticate via POST /oauth/token",
            hint="Obtain a fresh token from POST /oauth/token.",
        )

    api_key, expires_at = cached
    if time.time() > expires_at:
        _key_cache.pop(key_hash, None)
        raise TokenExpiredError(
            "Token expired. Request a new one via POST /oauth/token",
            hint="Refresh OAuth token or use X-API-Key.",
        )
    _evict_expired_tokens()
    return api_key
