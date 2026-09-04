"""JWT auth: Bearer tokens carry the Fernet-encrypted API key in the payload (stateless)."""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import time
from collections.abc import Mapping
from typing import Any, Optional

import jwt
from cryptography.fernet import Fernet

from errors import AuthError, TokenExpiredError, TokenInvalidError

logger = logging.getLogger("asterwise_mcp.auth")

JWT_ALGORITHM = "HS256"
TOKEN_TTL = 3600
ISSUER = "asterwise-mcp"



def _get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET environment variable is not set. Cannot issue or verify tokens."
        )
    if len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET must be at least 32 characters. Generate one with: "
            "python3 -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return secret


def _get_fernet() -> Fernet:
    """
    Derive a Fernet key from JWT_SECRET.
    Fernet requires a 32-byte URL-safe base64 key.
    We derive it deterministically from JWT_SECRET using SHA-256 so no new env var is needed.
    """
    secret = _get_jwt_secret()
    key_bytes = hashlib.sha256(secret.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def _hash_key(api_key: str) -> str:
    """One-way hash of API key for identification (sub claim)."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def create_token(api_key: str) -> str:
    """
    Create a signed JWT. The API key is Fernet-encrypted in the payload; validation is stateless.
    """
    f = _get_fernet()
    encrypted_key = f.encrypt(api_key.encode("utf-8")).decode("utf-8")
    key_hash = _hash_key(api_key)
    now = time.time()
    expires_at = now + TOKEN_TTL
    payload: dict[str, Any] = {
        "sub": key_hash,
        "key": encrypted_key,
        "iat": int(now),
        "exp": int(expires_at),
        "iss": ISSUER,
    }
    token = jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)
    logger.info(
        "token_issued",
        extra={
            "key_hash_prefix": key_hash[:8],
            "expires_in": TOKEN_TTL,
        },
    )
    return token


def _fernet_from_secret(secret: str) -> Fernet:
    """Derive Fernet key from an arbitrary signing secret (same scheme as _get_fernet)."""
    key_bytes = hashlib.sha256(secret.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def decode_token(token: str) -> str:
    """
    Validate JWT signature and expiry, decrypt API key from payload (stateless).

    Accepts tokens signed with JWT_SECRET (client_credentials) or MCP_OAUTH_SECRET
    (authorization_code tokens from asterwise-api).
    """
    jwt_secret = os.getenv("JWT_SECRET")
    oauth_secret = os.getenv("MCP_OAUTH_SECRET")
    secrets_to_try: list[str] = []
    if jwt_secret:
        secrets_to_try.append(jwt_secret)
    if oauth_secret and oauth_secret not in secrets_to_try:
        secrets_to_try.append(oauth_secret)

    if not secrets_to_try:
        raise TokenInvalidError(
            "Invalid token. Request a new one via POST /oauth/token"
        )

    last_error: BaseException | None = None
    saw_expired = False  # an expired-but-validly-signed token beats "invalid"

    for secret in secrets_to_try:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[JWT_ALGORITHM],
                options={"require": ["sub", "exp", "iat", "iss", "key"]},
            )
        except jwt.ExpiredSignatureError as exc:
            last_error = exc
            saw_expired = True
            continue
        except jwt.InvalidTokenError as exc:
            last_error = exc
            continue

        if payload.get("iss") != ISSUER:
            last_error = jwt.InvalidTokenError("issuer mismatch")
            continue

        encrypted_key = payload.get("key")
        if not encrypted_key or not isinstance(encrypted_key, str):
            last_error = jwt.InvalidTokenError("missing key claim")
            continue

        key_hash = payload.get("sub")
        if not isinstance(key_hash, str) or not key_hash.strip():
            last_error = jwt.InvalidTokenError("invalid sub")
            continue

        try:
            f = _fernet_from_secret(secret)
            api_key = f.decrypt(encrypted_key.encode("utf-8")).decode("utf-8")
        except Exception as exc:
            last_error = exc
            continue

        return api_key

    if saw_expired or isinstance(last_error, jwt.ExpiredSignatureError):
        raise TokenExpiredError(
            "Token has expired. Request a new one via POST /oauth/token"
        ) from last_error
    raise TokenInvalidError(
        "Invalid token. Request a new one via POST /oauth/token"
    )


def _lower_headers(headers: Mapping[str, str] | dict[str, str]) -> dict[str, str]:
    return {str(k).lower(): v for k, v in headers.items()}


def looks_like_jwt(token: str) -> bool:
    """
    True when the value has the three dot-separated segments of a compact JWS.

    Asterwise API keys (``aw_`` + url-safe token) never contain dots, so anything
    without exactly two dots is treated as a raw API key rather than a token.
    """
    parts = token.split(".")
    return len(parts) == 3 and all(parts)


def resolve_bearer_token(token: str) -> str:
    """
    Turn a Bearer credential into an API key.

    JWTs issued by this server (or by asterwise-api for OAuth) are validated and
    the embedded key is returned. Any other value is passed through unchanged as a
    raw API key; asterwise-api validates it on every upstream call.

    Raises TokenExpiredError / TokenInvalidError only for malformed or bad JWTs.
    """
    if looks_like_jwt(token):
        return decode_token(token)
    return token


def extract_api_key(headers: Mapping[str, str] | dict[str, str]) -> Optional[str]:
    """
    Extract API key from normalized headers (Bearer first, then X-API-Key).

    The Bearer value may be a JWT from /oauth/token or a raw Asterwise API key.
    Returns None if neither header is present. Does not raise for missing auth.
    """
    h = _lower_headers(headers)
    auth_header = h.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            return resolve_bearer_token(token)
    api_key = h.get("x-api-key", "").strip()
    if api_key:
        return api_key
    return None


def validate_and_get_key(headers: Mapping[str, str] | dict[str, str]) -> str:
    """Return the API key or raise AuthError."""
    result = extract_api_key(headers)
    if not result:
        raise AuthError(
            "No API key provided. Pass X-API-Key header "
            "or Authorization: Bearer <token>. "
            "Get a free key at asterwise.com/dashboard"
        )
    return result
