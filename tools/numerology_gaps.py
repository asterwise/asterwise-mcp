"""New numerology gap tools — expression, soul urge, personality, maturity,
balance, karmic lessons, personal cycles."""

from __future__ import annotations

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
        name="asterwise_get_expression_number",
        description=(
            "Calculates the Expression (Destiny) number from the full name. "
            "Uses all letters with Pythagorean values, reducing each name part "
            "separately before summing (Goodwin method). Preserves master numbers "
            "11, 22, 33.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.number (int)\n"
            "data.is_master_number (bool)\n"
            "data.karmic_debt_number (int or null)\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_numerology_profile — includes expression but also "
            "all other core numbers, pinnacles, and challenges."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_expression_number(
        ctx: Context,
        name: str,
        response_format: ResponseFormat,
    ) -> str:
        """Expression (Destiny) number from name."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/expression", api_key, {"name": name}
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Expression number", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_expression_number", exc)

    @mcp.tool(
        name="asterwise_get_soul_urge_number",
        description=(
            "Calculates the Soul Urge (Heart's Desire) number from vowels "
            "(A, E, I, O, U) in the full name. Reduces each name part separately. "
            "Y is treated as a consonant.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.number, data.is_master_number, data.karmic_debt_number"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_soul_urge_number(
        ctx: Context,
        name: str,
        response_format: ResponseFormat,
    ) -> str:
        """Soul Urge number from vowels."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/soul-urge", api_key, {"name": name}
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Soul Urge number", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_soul_urge_number", exc)

    @mcp.tool(
        name="asterwise_get_personality_number",
        description=(
            "Calculates the Personality number from consonants in the full name. "
            "Reduces each name part separately. "
            "Represents the outer personality visible to others.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.number, data.is_master_number, data.karmic_debt_number"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_personality_number(
        ctx: Context,
        name: str,
        response_format: ResponseFormat,
    ) -> str:
        """Personality number from consonants."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/personality", api_key, {"name": name}
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Personality number", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_personality_number", exc)

    @mcp.tool(
        name="asterwise_get_maturity_number",
        description=(
            "Calculates the Maturity number from Life Path + Expression. "
            "Represents the underlying wish or desire that surfaces around age 35. "
            "Requires both name and birth date.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.maturity_number, data.life_path_number, "
            "data.expression_number, data.is_master_number"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_maturity_number(
        ctx: Context,
        name: str,
        date: str,
        response_format: ResponseFormat,
    ) -> str:
        """Maturity number (Life Path + Expression)."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/maturity", api_key, {"name": name, "date": date}
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Maturity number", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_maturity_number", exc)

    @mcp.tool(
        name="asterwise_get_balance_number",
        description=(
            "Calculates the Balance number from the first letter of each name part. "
            "Indicates how a person handles stress and unresolved issues.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.number, data.is_master_number"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_balance_number(
        ctx: Context,
        name: str,
        response_format: ResponseFormat,
    ) -> str:
        """Balance number from initials."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/balance", api_key, {"name": name}
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Balance number", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_balance_number", exc)

    @mcp.tool(
        name="asterwise_get_karmic_lessons",
        description=(
            "Identifies karmic lessons from the name — the digit values 1-9 "
            "that are absent from the name's letter values. "
            "Missing numbers indicate areas requiring development in this lifetime.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.karmic_lessons (int array — missing digits 1-9, sorted)\n"
            "data.has_karmic_lessons (bool)"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_karmic_lessons(
        ctx: Context,
        name: str,
        response_format: ResponseFormat,
    ) -> str:
        """Karmic lessons from name."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().post(
                "/v1/numerology/karmic-lessons", api_key, {"name": name}
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Karmic lessons", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_karmic_lessons", exc)

    @mcp.tool(
        name="asterwise_get_personal_cycles",
        description=(
            "Returns the Personal Year, Personal Month, and Personal Day numbers "
            "for a birth date and target date. Defaults to today if not provided.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "date: birth date YYYY-MM-DD\n"
            "year (optional int): target year, defaults to current year\n"
            "month (optional int 1-12): target month, defaults to current month\n"
            "day (optional int 1-31): target day. Personal Day only included "
            "when day is provided.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.personal_year (int)\n"
            "data.personal_month (int)\n"
            "data.personal_day (int or null — only when day provided)\n"
            "data.target_year, data.target_month, data.target_day\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_personal_year — basic personal year only, no month/day."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_personal_cycles(
        ctx: Context,
        date: str,
        response_format: ResponseFormat,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
    ) -> str:
        """Personal Year, Month, and Day cycles."""
        try:
            api_key = await require_api_key(ctx)
            body: dict = {"date": date}
            if year is not None:
                body["year"] = year
            if month is not None:
                body["month"] = month
            if day is not None:
                body["day"] = day
            data = await get_client().post(
                "/v1/numerology/personal-cycles", api_key, body
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Personal cycles", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_personal_cycles", exc)
