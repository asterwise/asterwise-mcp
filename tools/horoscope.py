"""Horoscope, Gochar, and transit analysis."""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import ValidationError

from client import _safe_path_segment, get_client
from errors import AsterwiseMCPError
from models import BirthData, HoroscopePeriod, ResponseFormat, birth_dict
from runtime import (
    STANDARD_ANNOTATIONS,
    format_tool_result,
    invalid_params,
    require_api_key,
    structured_markdown,
    tool_error,
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
        moon_sign: str,
        period: HoroscopePeriod,
        response_format: ResponseFormat,
    ) -> str:
        """Moon-sign horoscope by period."""
        try:
            api_key = await require_api_key()
            path = (
                f"/v1/horoscope/{_safe_path_segment(period.value)}/"
                f"{_safe_path_segment(moon_sign.lower())}"
            )
            data = await get_client().get(path, api_key)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Horoscope ({period.value}, {moon_sign})", d),
            )
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            invalid_params(str(exc))
        except Exception as exc:
            tool_error(f"Unexpected error: {type(exc).__name__}: {exc}")

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
        birth: BirthData,
        response_format: ResponseFormat,
    ) -> str:
        """Gochar from natal chart."""
        try:
            api_key = await require_api_key()
            data = await get_client().post("/v1/astro/gochar", api_key, birth_dict(birth))
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Gochar (transits)", d),
            )
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            invalid_params(str(exc))
        except Exception as exc:
            tool_error(f"Unexpected error: {type(exc).__name__}: {exc}")

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
        birth: BirthData,
        from_date: str,
        to_date: str,
        response_format: ResponseFormat,
    ) -> str:
        """Date-range transits."""
        try:
            api_key = await require_api_key()
            body = {**birth_dict(birth), "from_date": from_date, "to_date": to_date}
            data = await get_client().post("/v1/astro/transits", api_key, body)
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Transits {from_date} → {to_date}", d),
            )
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            invalid_params(str(exc))
        except Exception as exc:
            tool_error(f"Unexpected error: {type(exc).__name__}: {exc}")
