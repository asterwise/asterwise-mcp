"""Centralized error types and HTTP error mapping for the Asterwise MCP proxy."""

from __future__ import annotations


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
    ) -> None:
        super().__init__(message, hint=hint)
        self.status_code = status_code
        self.api_request_id = api_request_id


# 422 codes that describe the request itself; the others (no sunrise at a
# polar latitude, an instant outside the solar day) are about the sky, so
# telling the model to fix a field would send it after the wrong cause.
_INPUT_ERROR_CODES = frozenset({
    "validation_error",
    "invalid_request_body",
    "location_required",
    "geocode_query_too_short",
})


def map_http_status_to_message(
    status_code: int, detail: str | None, error_code: str | None = None
) -> str:
    """Map HTTP status codes to actionable messages for LLM clients."""
    if status_code == 401:
        return (
            "Invalid API key. Get one free at https://asterwise.com/dashboard. "
            "Send a valid key via the X-API-Key header or a Bearer token from POST /oauth/token."
        )
    if status_code == 422:
        if error_code is not None and error_code not in _INPUT_ERROR_CODES:
            return (
                f"The Asterwise API could not compute this ({error_code}): "
                f"{detail or 'no further detail'}. The inputs are well-formed; "
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
        return (
            "Rate limit exceeded. Please retry after a short wait."
        )
    if status_code >= 500:
        return (
            "Asterwise API error. Check status at https://status.asterwise.com and retry later."
        )
    if detail:
        return f"Asterwise API request failed (HTTP {status_code}): {detail}"
    return f"Asterwise API request failed with HTTP {status_code}."
