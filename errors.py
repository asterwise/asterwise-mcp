"""Centralized error types and HTTP error mapping for the Asterwise MCP proxy."""

from __future__ import annotations

from typing import Any


class AsterwiseMCPError(Exception):
    """Base error for this server."""

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.hint = hint


class AuthError(AsterwiseMCPError):
    """Missing or invalid authentication."""

    pass


class TokenExpiredError(AuthError):
    """JWT access token has expired."""

    pass


class TokenInvalidError(AuthError):
    """JWT is malformed or signature invalid."""

    pass


class AsterwiseAPIError(AsterwiseMCPError):
    """Upstream Asterwise API returned an error.

    status_code and api_request_id identify the failing API call; the id is
    the API's X-Request-ID, searchable in its logs and Sentry.
    """

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        status_code: int | None = None,
        api_request_id: str | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message, hint=hint)
        self.status_code = status_code
        self.api_request_id = api_request_id
        self.error_code = error_code


# 422 codes that describe the request itself; the others (no sunrise at a
# polar latitude, an instant outside the solar day) are about the sky, so
# telling the model to fix a field would send it after the wrong cause.
_INPUT_ERROR_CODES = frozenset({
    "validation_error",
    "invalid_request_body",
    "location_required",
    "geocode_query_too_short",
})


# Some validation_error 422s are still about the sky: KP inside the polar
# circles has no Placidus cusps. The API marks those items so a client can
# tell them from a malformed request.
_SKY_SIDE_ISSUES = frozenset({"no_quadrant_houses_at_this_latitude"})


def details_are_sky_side(details: Any) -> bool:
    """True when any error detail says the input itself was fine."""
    if not isinstance(details, list):
        return False
    return any(
        isinstance(item, dict)
        and (item.get("issue") in _SKY_SIDE_ISSUES or item.get("input_format_ok") is True)
        for item in details
    )


# The API refuses with 429 for limits that need different answers from the
# caller: the monthly limit only lifts on the 1st (UTC) or with a higher plan,
# while the per-minute ones lift within a minute. One "retry shortly" message
# for all of them sent a tester round in circles for hours (2026-10-26).
MONTHLY_LIMIT_CODE = "monthly_usage_limit_exceeded"


def _rate_limit_message(error_code: str | None, detail: str | None, retry_after: int | None) -> str:
    wait = f"{retry_after} seconds" if retry_after and retry_after > 0 else "a minute"
    if error_code == MONTHLY_LIMIT_CODE:
        said = f" The API said: {detail.rstrip('.')}." if detail else ""
        return (
            f"Monthly call limit reached ({error_code}): this Asterwise account has used every "
            "call its plan includes this month. Retrying will not help: the limit resets on the "
            "1st of next month at 00:00 UTC, or sooner with a higher plan at "
            "https://asterwise.com/dashboard." + said
        )
    if error_code == "burst_limit_exceeded":
        return (
            f"Per-minute limit reached ({error_code}): this account's plan allows a set number "
            f"of calls a minute. Wait {wait}, then continue at a slower pace."
        )
    if error_code == "ip_rate_limit_exceeded":
        return (
            f"Per-network limit reached ({error_code}): too many calls came from this network "
            f"in the last minute. Wait {wait}, then continue at a slower pace."
        )
    code = f" ({error_code})" if error_code else ""
    said = f" The API said: {detail.rstrip('.')}." if detail else ""
    return f"Rate limit reached{code}. Wait {wait} before retrying." + said


def map_http_status_to_message(
    status_code: int,
    detail: str | None,
    error_code: str | None = None,
    *,
    sky_side: bool = False,
    retry_after: int | None = None,
) -> str:
    """Map HTTP status codes to actionable messages for LLM clients."""
    if status_code == 401:
        return (
            "Invalid API key. Get one free at https://asterwise.com/dashboard. "
            "Send a valid key via the X-API-Key header or a Bearer token from POST /oauth/token."
        )
    if status_code == 422:
        if sky_side or (error_code is not None and error_code not in _INPUT_ERROR_CODES):
            return (
                f"The Asterwise API could not compute this ({error_code}): "
                f"{(detail or 'no further detail').rstrip('.')}. The inputs are well-formed; "
                "retrying with the same values will give the same answer."
            )
        extra = f" Details: {detail}" if detail else ""
        return (
            "Invalid parameters — the Asterwise API rejected the request body or query."
            f"{extra} "
            "Fix the field mentioned in the error (check date format YYYY-MM-DD, time HH:MM, "
            "latitude/longitude ranges, and enum values) and retry."
        )
    if status_code == 429:
        return _rate_limit_message(error_code, detail, retry_after)
    if status_code >= 500:
        return (
            "Asterwise API error. Check status at https://status.asterwise.com and retry later."
        )
    if detail:
        return f"Asterwise API request failed (HTTP {status_code}): {detail}"
    return f"Asterwise API request failed with HTTP {status_code}."
