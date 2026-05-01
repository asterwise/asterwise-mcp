"""Tarot tools — 78-card Rider-Waite-Smith deck."""

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
    invalid_params,
    require_api_key,
    structured_markdown,
    tool_error,
    raise_validation_error,
    unexpected_tool_error,
)

_VALID_SUITS = frozenset({"wands", "cups", "swords", "pentacles"})
_VALID_PLANETS = frozenset({
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"
})


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="asterwise_get_tarot_cards",
        description=(
            "Returns the complete 78-card Rider-Waite-Smith deck with full metadata. "
            "Each card includes id (slug), name, arcana_type (major/minor), suit, "
            "number, element, astrology_correspondence, upright and reversed meanings, "
            "keywords for both orientations, yes/no polarity, and visual description.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data[] — 78 card objects, each:\n"
            "  id (slug e.g. 'the-fool', 'ace-of-wands')\n"
            "  name, arcana_type, suit (null for major arcana), number\n"
            "  element, astrology_correspondence\n"
            "  keywords_upright[], keywords_reversed[]\n"
            "  upright_meaning, reversed_meaning\n"
            "  yes_no ('yes'|'no'|'maybe'), description"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_tarot_cards(
        ctx: Context,
        response_format: ResponseFormat,
    ) -> str:
        """All 78 tarot cards."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                "/v1/tarot/cards", api_key, timeout=15.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("78-card tarot deck", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_tarot_cards", exc)

    @mcp.tool(
        name="asterwise_get_tarot_card",
        description=(
            "Returns full data for a single card by its slug ID.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "card_id: slug identifier. Examples: 'the-fool', 'ace-of-wands', "
            "'king-of-cups', 'the-world', 'ten-of-swords', 'queen-of-pentacles'.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data — single card object with all metadata fields."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_tarot_card(
        ctx: Context,
        card_id: str,
        response_format: ResponseFormat,
    ) -> str:
        """Single tarot card by slug ID."""
        try:
            api_key = await require_api_key(ctx)
            from client import safe_segment
            data = await get_client().get(
                f"/v1/tarot/cards/{safe_segment(card_id)}", api_key, timeout=10.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown(f"Tarot card: {card_id}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_tarot_card", exc)

    @mcp.tool(
        name="asterwise_get_tarot_major_arcana",
        description=(
            "Returns all 22 Major Arcana cards (The Fool through The World). "
            "Major Arcana represent archetypal life themes and major life events."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_tarot_major_arcana(
        ctx: Context,
        response_format: ResponseFormat,
    ) -> str:
        """22 Major Arcana cards."""
        try:
            api_key = await require_api_key(ctx)
            data = await get_client().get(
                "/v1/tarot/major-arcana", api_key, timeout=10.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Major Arcana", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_tarot_major_arcana", exc)

    @mcp.tool(
        name="asterwise_get_tarot_suit",
        description=(
            "Returns all 14 cards in a given suit.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "suit: one of 'wands', 'cups', 'swords', 'pentacles'.\n"
            "Wands=fire/career, Cups=water/emotions, "
            "Swords=air/intellect, Pentacles=earth/material."
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_tarot_suit(
        ctx: Context,
        suit: str,
        response_format: ResponseFormat,
    ) -> str:
        """Tarot cards by suit."""
        try:
            api_key = await require_api_key(ctx)
            if suit.lower() not in _VALID_SUITS:
                invalid_params(
                    f"suit must be one of: wands, cups, swords, pentacles. "
                    f"Got: {suit!r}"
                )
            from client import safe_segment
            data = await get_client().get(
                f"/v1/tarot/suits/{safe_segment(suit.lower())}", api_key, timeout=10.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown(f"Suit of {suit}", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_tarot_suit", exc)

    @mcp.tool(
        name="asterwise_get_tarot_card_of_the_day",
        description=(
            "Returns a deterministic daily tarot card. "
            "The same card is returned for all requests on the same date — "
            "seeded by SHA-256 hash of the date string. "
            "All users see the same card on the same day.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "date (optional YYYY-MM-DD): defaults to today.\n"
            "allow_reversed (optional bool): default false.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.date, data.card (full card object), data.is_reversed\n"
            "data.active_meaning (upright or reversed meaning per orientation)\n"
            "data.active_keywords[]"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=False,
        ),
    )
    async def asterwise_get_tarot_card_of_the_day(
        ctx: Context,
        response_format: ResponseFormat,
        date: str | None = None,
        allow_reversed: bool = False,
    ) -> str:
        """Daily tarot card (deterministic by date)."""
        try:
            api_key = await require_api_key(ctx)
            params: dict = {"allow_reversed": allow_reversed}
            if date:
                params["date"] = date
            data = await get_client().get(
                "/v1/tarot/card-of-the-day", api_key, params, timeout=10.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Card of the day", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_tarot_card_of_the_day", exc)

    @mcp.tool(
        name="asterwise_draw_tarot_cards",
        description=(
            "Draw N random unique cards from the 78-card deck using "
            "cryptographic randomness. Each API call produces a fresh draw.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "count (int 1-78, default 1): number of cards to draw.\n"
            "allow_reversed (bool, default false): if true, each card independently "
            "has a 50% chance of reversal.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.cards[] — each: card (full object), is_reversed, "
            "active_meaning, active_keywords[]\n"
            "data.count, data.allow_reversed"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=False, openWorldHint=False,
        ),
    )
    async def asterwise_draw_tarot_cards(
        ctx: Context,
        response_format: ResponseFormat,
        count: int = 1,
        allow_reversed: bool = False,
    ) -> str:
        """Draw random tarot cards."""
        try:
            api_key = await require_api_key(ctx)
            if not 1 <= count <= 78:
                invalid_params("count must be between 1 and 78.")
            data = await get_client().post(
                "/v1/tarot/draw", api_key,
                {"count": count, "allow_reversed": allow_reversed},
                timeout=10.0,
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown(f"Tarot draw ({count} cards)", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_draw_tarot_cards", exc)

    @mcp.tool(
        name="asterwise_get_tarot_three_card_spread",
        description=(
            "Past / Present / Future spread. "
            "Draws 3 unique cards assigned to positions: "
            "past (what led here), present (current situation), "
            "future (where this leads).\n\n"
            "SECTION: INPUT CONTRACT\n"
            "allow_reversed (bool, default false)\n"
            "question (optional string max 500 chars)\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.spread_type ('three_card')\n"
            "data.positions[] — 3 objects: card, is_reversed, position, "
            "position_meaning, active_meaning, active_keywords[]\n"
            "data.question (echoed if provided)"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=False, openWorldHint=False,
        ),
    )
    async def asterwise_get_tarot_three_card_spread(
        ctx: Context,
        response_format: ResponseFormat,
        allow_reversed: bool = False,
        question: str | None = None,
    ) -> str:
        """Three-card tarot spread (Past/Present/Future)."""
        try:
            api_key = await require_api_key(ctx)
            body: dict = {"allow_reversed": allow_reversed}
            if question:
                body["question"] = question
            data = await get_client().post(
                "/v1/tarot/spread/three-card", api_key, body, timeout=10.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Three-card spread", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_tarot_three_card_spread", exc)

    @mcp.tool(
        name="asterwise_get_tarot_celtic_cross",
        description=(
            "Full 10-card Celtic Cross spread — the most comprehensive tarot spread. "
            "Positions: present, challenge, root, past, possible outcome, "
            "near future, self, external influences, hopes and fears, final outcome.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "allow_reversed (bool, default false)\n"
            "question (optional string max 500 chars)\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.spread_type ('celtic_cross')\n"
            "data.positions[] — 10 objects: card, is_reversed, position, "
            "position_meaning, active_meaning, active_keywords[]\n"
            "data.question (echoed if provided)"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=False, openWorldHint=False,
        ),
    )
    async def asterwise_get_tarot_celtic_cross(
        ctx: Context,
        response_format: ResponseFormat,
        allow_reversed: bool = False,
        question: str | None = None,
    ) -> str:
        """Celtic Cross 10-card spread."""
        try:
            api_key = await require_api_key(ctx)
            body: dict = {"allow_reversed": allow_reversed}
            if question:
                body["question"] = question
            data = await get_client().post(
                "/v1/tarot/spread/celtic-cross", api_key, body, timeout=10.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Celtic Cross spread", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_tarot_celtic_cross", exc)

    @mcp.tool(
        name="asterwise_get_tarot_yes_no",
        description=(
            "Draw one card for a yes/no answer.\n\n"
            "SECTION: ANSWER LOGIC\n"
            "yes-polarity card upright → 'yes' (strong confidence)\n"
            "yes-polarity card reversed → 'maybe' (leaning)\n"
            "no-polarity card upright → 'no' (strong)\n"
            "no-polarity card reversed → 'maybe' (leaning)\n"
            "maybe-polarity card → 'maybe' (unclear)\n\n"
            "SECTION: INPUT CONTRACT\n"
            "allow_reversed (bool, default true — recommended for yes/no)\n"
            "question (optional string)\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.card (full card object)\n"
            "data.is_reversed\n"
            "data.answer ('yes'|'no'|'maybe')\n"
            "data.confidence ('strong'|'leaning'|'unclear')\n"
            "data.active_meaning\n"
            "data.question (echoed)"
        ),
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=False, openWorldHint=False,
        ),
    )
    async def asterwise_get_tarot_yes_no(
        ctx: Context,
        response_format: ResponseFormat,
        allow_reversed: bool = True,
        question: str | None = None,
    ) -> str:
        """Yes/No tarot reading."""
        try:
            api_key = await require_api_key(ctx)
            body: dict = {"allow_reversed": allow_reversed}
            if question:
                body["question"] = question
            data = await get_client().post(
                "/v1/tarot/spread/yes-no", api_key, body, timeout=10.0
            )
            return format_tool_result(
                data, response_format,
                lambda d: structured_markdown("Yes/No reading", d),
            )
        except McpError:
            raise
        except AsterwiseMCPError as exc:
            tool_error(str(exc))
        except ValidationError as exc:
            raise_validation_error(exc)
        except Exception as exc:
            unexpected_tool_error("asterwise_get_tarot_yes_no", exc)
