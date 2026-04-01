"""Horoscope, Gochar, and transit analysis."""

from __future__ import annotations

from fastmcp import Context, FastMCP

from mcp.shared.exceptions import McpError
from pydantic import ValidationError

from client import get_client, safe_segment
from errors import AsterwiseMCPError
from models import BirthData, HoroscopePeriod, ResponseFormat
from runtime import (
    STANDARD_ANNOTATIONS,
    format_tool_result,
    invalid_params,
    require_api_key,
    structured_markdown,
    tool_error,
    raise_validation_error,
    unexpected_tool_error,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(
        name="asterwise_get_horoscope",
        description=(
            "Fresh horoscope for a Moon sign and period — computed from current planetary positions, not "
            "static text. Source: classical sign-lord and transit synthesis.\n"
            "Inputs: moon_sign (e.g. libra), period (daily/weekly/monthly/yearly), response_format.\n"
            "Returns: Generated reading."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_horoscope(
        ctx: Context,
        moon_sign: str,
        period: HoroscopePeriod,
        response_format: ResponseFormat
    ) -> str:
        """Moon-sign horoscope by period."""
        try:
            api_key = await require_api_key(ctx)
            path = (
                f"/v1/horoscope/{safe_segment(period.value)}/"
                f"{safe_segment(moon_sign.lower())}"
            )
            data = await get_client().get(path, api_key, timeout=10.0)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Horoscope ({period.value}, {moon_sign})", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_horoscope", exc)

    @mcp.tool(
        name="asterwise_get_gochar",
        description=(
            "Current planetary transits (Gochar) vs natal chart — houses transited and interpretations. "
            "Source: classical Gochar.\n"
            "Inputs: BirthData, response_format.\n"
            "Returns: Transit positions and effects."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_gochar(
        ctx: Context,
        birth: BirthData,
        response_format: ResponseFormat
    ) -> str:
        """Gochar from natal chart."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/astro/gochar", api_key, birth.to_api_dict(), timeout=10.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Gochar (transits)", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_gochar", exc)

    @mcp.tool(
        name="asterwise_get_transits",
        description=(
            "Transit analysis over a date range vs natal chart. Source: Gochar with date range.\n"
            "Inputs: BirthData, from_date, to_date (YYYY-MM-DD), response_format.\n"
            "Returns: Transit events in range."
        ),
        annotations=STANDARD_ANNOTATIONS,
    )
    async def asterwise_get_transits(
        ctx: Context,
        birth: BirthData,
        from_date: str,
        to_date: str,
        response_format: ResponseFormat
    ) -> str:
        """Date-range transits."""
        try:
            api_key = await require_api_key(ctx)
            body = {**birth.to_api_dict(), "from_date": from_date, "to_date": to_date}
            data = await get_client().post(
                "/v1/astro/transits", api_key, body, timeout=10.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Transits {from_date} → {to_date}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_transits", exc)
