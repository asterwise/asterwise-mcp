"""Auth: JWT hash cache, extraction, eviction."""

from __future__ import annotations

import base64
import json
import os
import time
from unittest.mock import patch

import jwt as pyjwt
import pytest

from auth import (
    TOKEN_TTL,
    TokenExpiredError,
    TokenInvalidError,
    _get_fernet,
    _hash_key,
    create_token,
    decode_token,
    extract_api_key,
    looks_like_jwt,
    resolve_bearer_token,
    validate_and_get_key,
)
from errors import AuthError


class TestTokenCreation:
    def test_create_token_returns_string(self) -> None:
        token = create_token("test-key-abc123")
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_token_does_not_contain_raw_key(self) -> None:
        api_key = "my-secret-api-key-xyz"
        token = create_token(api_key)
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        payload_b64 += "=" * (padding % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        assert api_key not in json.dumps(payload)
        assert api_key not in payload.get("sub", "")

    def test_token_sub_is_hash_not_key(self) -> None:
        api_key = "test-api-key"
        token = create_token(api_key)
        payload_b64 = token.split(".")[1]
        padding = 4 - len(payload_b64) % 4
        payload_b64 += "=" * (padding % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        assert payload["sub"] == _hash_key(api_key)
        assert "key" in payload
        assert isinstance(payload["key"], str)
        assert payload["iss"] == "asterwise-mcp"

    def test_missing_jwt_secret_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="JWT_SECRET"):
                create_token("any-key")

    def test_short_jwt_secret_raises(self) -> None:
        with patch.dict(os.environ, {"JWT_SECRET": "tooshort"}):
            with pytest.raises(RuntimeError, match="32 characters"):
                create_token("any-key")


class TestTokenDecoding:
    def test_roundtrip_returns_original_key(self) -> None:
        api_key = "roundtrip-test-key-12345"
        token = create_token(api_key)
        recovered = decode_token(token)
        assert recovered == api_key

    def test_expired_jwt_raises_expired_error(self) -> None:
        api_key = "expiry-test-key"
        f = _get_fernet()
        enc = f.encrypt(api_key.encode("utf-8")).decode("utf-8")
        payload = {
            "sub": _hash_key(api_key),
            "key": enc,
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,
            "iss": "asterwise-mcp",
        }
        expired_token = pyjwt.encode(
            payload,
            os.environ["JWT_SECRET"],
            algorithm="HS256",
        )
        with pytest.raises(TokenExpiredError):
            decode_token(expired_token)

    def test_tampered_token_raises_invalid(self) -> None:
        with pytest.raises(TokenInvalidError):
            decode_token("not.a.valid.jwt")

    def test_missing_key_claim_raises_invalid(self) -> None:
        payload = {
            "sub": _hash_key("some-key"),
            "iat": int(time.time()),
            "exp": int(time.time()) + TOKEN_TTL,
            "iss": "asterwise-mcp",
        }
        fake_token = pyjwt.encode(
            payload,
            os.environ["JWT_SECRET"],
            algorithm="HS256",
        )
        with pytest.raises(TokenInvalidError):
            decode_token(fake_token)

    def test_invalid_encrypted_key_raises_invalid(self) -> None:
        payload = {
            "sub": _hash_key("some-key"),
            "key": "not-valid-fernet-ciphertext",
            "iat": int(time.time()),
            "exp": int(time.time()) + TOKEN_TTL,
            "iss": "asterwise-mcp",
        }
        fake_token = pyjwt.encode(
            payload,
            os.environ["JWT_SECRET"],
            algorithm="HS256",
        )
        with pytest.raises(TokenInvalidError, match="Invalid token"):
            decode_token(fake_token)

    def test_wrong_issuer_raises_invalid(self) -> None:
        payload = {
            "sub": "somehash",
            "iat": int(time.time()),
            "exp": int(time.time()) + TOKEN_TTL,
            "iss": "some-other-server",
        }
        token = pyjwt.encode(
            payload,
            os.environ["JWT_SECRET"],
            algorithm="HS256",
        )
        with pytest.raises(TokenInvalidError):
            decode_token(token)


class TestKeyExtraction:
    def test_bearer_token_extracts_key(self) -> None:
        api_key = "bearer-test-key-abc"
        token = create_token(api_key)
        headers = {"authorization": f"Bearer {token}"}
        result = extract_api_key(headers)
        assert result == api_key

    def test_x_api_key_header_works(self) -> None:
        headers = {"x-api-key": "direct-api-key"}
        result = extract_api_key(headers)
        assert result == "direct-api-key"

    def test_bearer_raw_api_key_passes_through(self) -> None:
        # README quick-start: Authorization: Bearer <aw_ key>, no JWT involved
        raw = "aw_" + "x" * 43
        result = extract_api_key({"authorization": f"Bearer {raw}"})
        assert result == raw

    def test_bearer_raw_key_is_case_insensitive_scheme(self) -> None:
        raw = "aw_" + "y" * 43
        assert extract_api_key({"Authorization": f"bearer {raw}"}) == raw

    def test_bearer_malformed_jwt_still_rejected(self) -> None:
        # Three dot-separated segments -> treated as a JWT and must fail closed
        with pytest.raises(TokenInvalidError):
            extract_api_key({"authorization": "Bearer aaa.bbb.ccc"})

    def test_bearer_expired_jwt_still_rejected(self) -> None:
        with patch("auth.time.time", return_value=1000.0):
            token = create_token("expired-key")
        with pytest.raises(TokenExpiredError):
            extract_api_key({"authorization": f"Bearer {token}"})

    def test_looks_like_jwt_shape(self) -> None:
        assert looks_like_jwt("a.b.c")
        assert not looks_like_jwt("aw_abc123")
        assert not looks_like_jwt("a.b")
        assert not looks_like_jwt("a..c")
        assert not looks_like_jwt("a.b.c.d")

    def test_resolve_bearer_token_roundtrip_jwt(self) -> None:
        token = create_token("roundtrip-key")
        assert resolve_bearer_token(token) == "roundtrip-key"
        assert resolve_bearer_token("aw_raw") == "aw_raw"

    def test_bearer_takes_priority_over_api_key(self) -> None:
        api_key = "priority-test-key"
        token = create_token(api_key)
        headers = {
            "authorization": f"Bearer {token}",
            "x-api-key": "should-be-ignored",
        }
        result = extract_api_key(headers)
        assert result == api_key

    def test_missing_auth_returns_none(self) -> None:
        result = extract_api_key({})
        assert result is None

    def test_validate_and_get_key_raises_on_missing(self) -> None:
        with pytest.raises(AuthError, match="No API key"):
            validate_and_get_key({})


class TestStatelessDecode:
    def test_token_valid_without_any_server_state(self) -> None:
        """JWT validation is stateless: nothing server-side is needed to decode."""
        api_key = "stateless-test-key-abc123"
        token = create_token(api_key)
        assert decode_token(token) == api_key

    def test_decode_token_accepts_sub_not_equal_to_key_hash(self) -> None:
        """asterwise-api authorization_code JWTs use account UUID as sub, not _hash_key(api_key)."""
        api_key = "oauth-style-raw-key-xyz"
        f = _get_fernet()
        enc = f.encrypt(api_key.encode("utf-8")).decode("utf-8")
        payload = {
            "sub": "550e8400-e29b-41d4-a716-446655440000",
            "key": enc,
            "iat": int(time.time()),
            "exp": int(time.time()) + TOKEN_TTL,
            "iss": "asterwise-mcp",
        }
        token = pyjwt.encode(payload, os.environ["JWT_SECRET"], algorithm="HS256")
        assert decode_token(token) == api_key
