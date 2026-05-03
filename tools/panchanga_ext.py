"""Tamil Panchanga and Hindu festival calendar MCP tools."""

from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP
from mcp.shared.exceptions import McpError
import mcp.types as mcp_types
from pydantic import ValidationError

from client import get_client
from errors import AsterwiseMCPError
from models import ResponseFormat
from runtime import (
    format_tool_result,
    require_api_key,
    structured_markdown,
    tool_error,
    raise_validation_error,
    unexpected_tool_error,
)


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="asterwise_get_tamil_panchanga",
        description="Returns Tamil-specific Panchanga for a date and location: all four inauspicious periods (Rahu Kalam, Yamagandam, Kuligai, Emagandam), Nalla Neram (auspicious daytime windows between inauspicious periods), and the Tamil solar month name based on the Sun's sidereal sign at sunrise.\n\nSECTION: WHAT THIS TOOL COVERS\nRahu Kalam, Yamagandam (Yamakanda), Kuligai (Gulika), and Emagandam divide the daytime into eight equal parts from sunrise to sunset following classical Tamil almanac weekday tables. Nalla Neram is every gap between the four inauspicious periods — the auspicious windows left for commencing ventures. Tamil solar month follows the Sun's Lahiri sidereal sign at local sunrise (Chithirai when Sun is in Mesha, through Panguni when Sun is in Meena). This tool does not return Vedic Panchanga limbs (asterwise_get_panchanga) or the standard Rahu/Gulika/Yamaganda breakdown used in North Indian tradition (asterwise_get_rahu_kaal).\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: asterwise_get_panchanga — for full Vedic five-limb panchanga of the same date.\n\nSECTION: INPUT CONTRACT\ndate: YYYY-MM-DD format.\nEither location (city name) OR latitude + longitude + timezone must be provided.\n\nSECTION: OUTPUT CONTRACT\ndata.date (string — YYYY-MM-DD)\ndata.sunrise (string — HH:MM local time)\ndata.sunset (string — HH:MM local time)\ndata.tamil_month (string — Tamil solar month name, e.g. 'Chithirai', 'Vaikasi')\ndata.rahu_kalam: start, end (HH:MM), duration_minutes (int), is_active (bool)\ndata.yamagandam: start, end (HH:MM), duration_minutes (int), is_active (bool)\ndata.kuligai: start, end (HH:MM), duration_minutes (int), is_active (bool)\ndata.emagandam: start, end (HH:MM), duration_minutes (int), is_active (bool)\ndata.nalla_neram: list of { start (HH:MM), end (HH:MM) } objects\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nFAST_LOOKUP — sunrise computation + lookup tables, no full natal chart.\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local): None — all validation upstream.\nINTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\nEdge cases:\n  — Polar latitudes where sunrise cannot be computed → MCP INTERNAL_ERROR.\n  — Emagandam part table: Sun=5, Mon=4, Tue=3, Wed=2, Thu=8, Fri=1, Sat=7.\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_rahu_kaal — North Indian Rahu/Gulika/Yamaganda only; no Emagandam, Nalla Neram, or Tamil month.\nasterwise_get_panchanga — five Vedic limbs (tithi, vara, nakshatra, yoga, karana); not Tamil-specific periods.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_tamil_panchanga(
        ctx: Context,
        date: str,
        response_format: ResponseFormat,
        location: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        timezone: str | None = None,
    ) -> str:
        """Compute Tamil Panchanga for a date and location."""
        try:
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {"date": date}
            if location:
                params["location"] = location
            if latitude is not None:
                params["latitude"] = latitude
            if longitude is not None:
                params["longitude"] = longitude
            if timezone:
                params["timezone"] = timezone
            data = await get_client().get(
                "/v1/astro/panchanga/tamil", api_key, params, timeout=15.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown("Tamil Panchanga", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_tamil_panchanga", exc)

    @mcp.tool(
        name="asterwise_get_festival_calendar",
        description="Computes all major Hindu festival dates for a given year and location. Returns 20 pan-Hindu festivals including solar sankrantis (Makar Sankranti, Vaisakhi) and tithi-based festivals (Diwali, Holi, Dussehra, Janmashtami, Ganesh Chaturthi, Ram Navami, and 12 others).\n\nSECTION: WHAT THIS TOOL COVERS\nAll dates are astronomically computed — no hardcoded calendar dates. Solar festivals (Makar Sankranti, Vaisakhi) use exact Swiss Ephemeris Sun ingress into Lahiri sidereal signs. Tithi festivals (all others) use Sun-Moon elongation at local sunrise: elongation = (moon_lon - sun_lon) % 360, tithi_index = int(elongation / 12), indices 0-14 = Shukla Paksha tithi 1-15, indices 15-29 = Krishna Paksha tithi 1-15. Location is required for sunrise-based tithi determination — the same astronomical event may fall on different calendar dates at different locations.\n\nSECTION: WORKFLOW\nBEFORE: None — standalone.\nAFTER: asterwise_get_panchanga — drill into full Panchanga detail for any specific festival date.\n\nSECTION: INPUT CONTRACT\nyear: integer 1900-2100.\nEither location (city name) OR latitude + longitude + timezone must be provided.\n\nSECTION: OUTPUT CONTRACT\ndata.year (int)\ndata.timezone (string — IANA timezone used)\ndata.total (int — number of festivals found)\ndata.festivals[] — chronologically sorted:\n  name (string — festival name)\n  date (string — YYYY-MM-DD)\n  type (string — 'solar' or 'tithi')\n  description (string — classical basis, e.g. which tithi of which lunar month)\n  significance (string — cultural and religious significance)\n\nSECTION: RESPONSE FORMAT\nresponse_format=json serialises the complete response as indented JSON — use this for programmatic parsing, typed clients, and downstream tool chaining. response_format=markdown renders the same data as a human-readable report. Both modes return identical underlying data — no fields are added, removed, or filtered by either mode.\n\nSECTION: COMPUTE CLASS\nSLOW_COMPUTE — scans all 365 days of the year per tithi festival (up to 20 date scans).\n\nSECTION: ERROR CONTRACT\nINVALID_PARAMS (local): None.\nINTERNAL_ERROR: Any upstream API failure or timeout → MCP INTERNAL_ERROR\nEdge cases:\n  — Sunrise-based tithi may differ by one day from printed almanac calendars (which use midnight or fixed-time rules).\n  — Rare years where a tithi is skipped may cause a festival to not be found (returns total < 20).\n\nSECTION: DO NOT CONFUSE WITH\nasterwise_get_panchanga_calendar — full Panchanga for every day of a month; not festival-specific.\nasterwise_get_muhurta — finds auspicious windows for activities; not a festival calendar.",
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def asterwise_get_festival_calendar(
        ctx: Context,
        year: int,
        response_format: ResponseFormat,
        location: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        timezone: str | None = None,
    ) -> str:
        """Compute Hindu festival calendar for a year and location."""
        try:
            api_key = await require_api_key(ctx)
            params: dict[str, Any] = {"year": year}
            if location:
                params["location"] = location
            if latitude is not None:
                params["latitude"] = latitude
            if longitude is not None:
                params["longitude"] = longitude
            if timezone:
                params["timezone"] = timezone
            data = await get_client().get(
                "/v1/astro/panchanga/festivals", api_key, params, timeout=120.0
            )
            return format_tool_result(
                data,
                response_format,
                lambda d: structured_markdown(f"Hindu Festival Calendar {year}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_festival_calendar", exc)
