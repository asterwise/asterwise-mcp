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
            "SECTION: WHAT THIS TOOL COVERS\n"
            "The complete 78-card Rider-Waite-Smith deck as structured JSON. Every card includes "
            "both upright and reversed meanings as separate fields, making orientation-aware "
            "interpretation automatic — the caller does not need to branch on is_reversed. "
            "The visual description field describes the imagery of each card. Use this endpoint "
            "to populate card databases, build card browsers, "
            "filter by element or astrology correspondence, or batch-load the deck for offline use.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone catalogue endpoint.\n"
            "AFTER: asterwise_draw_tarot_cards or asterwise_get_tarot_three_card_spread — use "
            "card data from this endpoint to build enriched display layers.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "response_format — Required: markdown | json (same as all Asterwise tools).\n"
            "No other parameters.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data[] — 78 card objects, each:\n"
            "  id (slug e.g. 'the-fool', 'ace-of-wands')\n"
            "  name, arcana_type, suit (null for major arcana), number\n"
            "  element, astrology_correspondence\n"
            "  keywords_upright[], keywords_reversed[]\n"
            "  upright_meaning, reversed_meaning\n"
            "  yes_no ('yes'|'no'|'maybe'), description\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json serialises the complete 78-card array as indented JSON.\n"
            "response_format=markdown renders a structured human-readable card catalogue.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP — data is static; no ephemeris or randomness involved.\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None — no input parameters beyond response_format.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_tarot_major_arcana — returns only the 22 Major Arcana subset.\n"
            "asterwise_get_tarot_suit — returns only the 14 cards of a single suit.\n"
            "asterwise_draw_tarot_cards — returns a random draw, not the catalogue."
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
            "Returns full structured data for a single card identified by its slug ID. "
            "Useful for card detail pages, single-card lookups, and displaying a specific "
            "card after the user selects one by name.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Returns one card object from the 78-card Rider-Waite-Smith deck. The slug is the "
            "card's unique identifier in lowercase-hyphenated format. All fields are identical "
            "to what asterwise_get_tarot_cards returns per card.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "card_id — Slug identifier for the card. Must be exact.\n"
            "  Major Arcana examples: 'the-fool', 'the-magician', 'the-high-priestess', "
            "'the-empress', 'the-emperor', 'the-hierophant', 'the-lovers', "
            "'the-chariot', 'strength', 'the-hermit', 'wheel-of-fortune', "
            "'justice', 'the-hanged-man', 'death', 'temperance', 'the-devil', "
            "'the-tower', 'the-star', 'the-moon', 'the-sun', 'judgement', 'the-world'\n"
            "  Minor Arcana pattern: '{rank}-of-{suit}'\n"
            "    Examples: 'ace-of-wands', 'two-of-cups', 'ten-of-swords', "
            "'page-of-pentacles', 'knight-of-wands', 'queen-of-cups', 'king-of-swords'\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data — single card object:\n"
            "  id (string — slug), name (string), arcana_type ('major'|'minor'), suit (string|null)\n"
            "  number (int — 0=Fool, 1–21=Major; 1=Ace, 11=Page, 12=Knight, 13=Queen, 14=King)\n"
            "  element (string), astrology_correspondence (string)\n"
            "  keywords_upright[] (string array), keywords_reversed[] (string array)\n"
            "  upright_meaning (string), reversed_meaning (string)\n"
            "  yes_no ('yes'|'no'|'maybe'), description (string — visual imagery)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — single card object as JSON.\n"
            "response_format=markdown — human-readable card detail.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None.\n"
            "INTERNAL_ERROR: Unknown card_id returns 404 upstream → MCP INTERNAL_ERROR\n"
            "  If the card is not found, check slug format: lowercase, hyphens, no spaces.\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_tarot_cards — returns all 78 cards in one call.\n"
            "asterwise_draw_tarot_cards — random draw, not a specific card."
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
            "Returns all 22 Major Arcana cards (The Fool through The World) as a structured array. "
            "Major Arcana represent universal archetypes and major life themes.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "The 22 Major Arcana are the foundation of the tarot — they deal with karmic and "
            "spiritual lessons, major life events, and universal forces. They are numbered 0 (The Fool) "
            "through 21 (The World). Each has an astrological correspondence and elemental association.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: asterwise_draw_tarot_cards — draw from this subset by filtering by arcana_type.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "response_format — Required: markdown | json.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data[] — 22 card objects, each identical to asterwise_get_tarot_card output.\n"
            "  Ordered 0–21 (The Fool through The World).\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — array of 22 card objects.\n"
            "response_format=markdown — formatted list.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_tarot_cards — full 78-card deck including Minor Arcana.\n"
            "asterwise_get_tarot_suit — 14 Minor Arcana cards by suit."
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
            "Returns all 14 cards in a given Minor Arcana suit as a structured array.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Each of the four suits has 14 cards: Ace through 10 plus Page, Knight, Queen, King. "
            "Elemental associations: Wands=fire (action, career, creativity), Cups=water (emotions, "
            "relationships, intuition), Swords=air (intellect, conflict, truth), Pentacles=earth "
            "(material, money, body, practical matters).\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "suit — One of exactly: 'wands', 'cups', 'swords', 'pentacles'.\n"
            "  Case-insensitive. Any other value is rejected locally with MCP INVALID_PARAMS.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data[] — 14 card objects for the requested suit, each identical to "
            "asterwise_get_tarot_card output. Ordered Ace through King.\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — array of 14 card objects.\n"
            "response_format=markdown — formatted list.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local):\n"
            "  — suit not in {wands, cups, swords, pentacles} → MCP INVALID_PARAMS immediately.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_tarot_major_arcana — 22 Major Arcana, not suit-based.\n"
            "asterwise_get_tarot_cards — full 78-card catalogue."
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
            "Returns a deterministic daily tarot card seeded by SHA-256 hash of the date string. "
            "The same card is returned for all callers on the same date — this is intentional. "
            "The daily card is not a reading for an individual but a collective daily energy.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Deterministic daily oracle: one card with its upright or reversed orientation "
            "(also deterministic when allow_reversed=true). The SHA-256 seed ensures that no "
            "two consecutive days produce the same card except by mathematical coincidence. "
            "The active_meaning field pre-computes the correct interpretation for the orientation — "
            "callers do not need to branch on is_reversed.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: asterwise_get_tarot_three_card_spread — for deeper daily reading context.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "date (optional string YYYY-MM-DD) — Date to get the card for. Defaults to today.\n"
            "  Example: '2026-05-01'\n"
            "allow_reversed (optional bool) — Default: false.\n"
            "  When true: reversed state is also deterministic (seeded by date+'_rev').\n"
            "  When false: card is always upright regardless of date.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.date (string — YYYY-MM-DD, the date this card represents)\n"
            "data.card — full card object (same shape as asterwise_get_tarot_card)\n"
            "data.is_reversed (bool)\n"
            "data.active_meaning (string — upright_meaning when not reversed, reversed_meaning when reversed)\n"
            "data.active_keywords[] (string array — upright or reversed keywords per orientation)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — full card object with metadata.\n"
            "response_format=markdown — human-readable daily card report.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP — deterministic, no randomness.\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None — date is validated upstream.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_draw_tarot_cards — random draw, different every call.\n"
            "asterwise_get_tarot_three_card_spread — positional reading with question context."
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
            "Draws N unique random cards from the 78-card deck using cryptographic randomness "
            "(Python secrets.SystemRandom). Every call is independent — there is no session state.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Random card selection for open readings, single-card daily pulls, or custom spread "
            "layouts. Uniqueness is guaranteed within a single draw — the same card cannot appear "
            "twice in one draw. The active_meaning field is pre-computed per orientation so callers "
            "do not need to branch on is_reversed.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: None — interpret drawn cards using their active_meaning and active_keywords fields.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "count (int 1–78, default 1) — Number of unique cards to draw.\n"
            "  Example: 1 (daily pull), 3 (simple reading), 10 (Celtic Cross), 78 (full deck shuffle).\n"
            "  Values outside 1–78 are rejected locally with MCP INVALID_PARAMS.\n"
            "allow_reversed (bool, default false) — When true, each drawn card independently has "
            "a 50% chance of reversal (cryptographically random, not seeded).\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.cards[] — array of count objects, each:\n"
            "  card — full card object (same shape as asterwise_get_tarot_card)\n"
            "  is_reversed (bool)\n"
            "  active_meaning (string — orientation-appropriate interpretation)\n"
            "  active_keywords[] (string array)\n"
            "  position (null — no position for free draws; use spread endpoints for positional reads)\n"
            "  position_meaning (null)\n"
            "data.count (int — echoed)\n"
            "data.allow_reversed (bool — echoed)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — structured draw result.\n"
            "response_format=markdown — human-readable card report.\n"
            "Both modes return identical underlying data.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP — cryptographic randomness, no ephemeris.\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local):\n"
            "  — count < 1 or count > 78 → MCP INVALID_PARAMS immediately.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_tarot_card_of_the_day — deterministic daily card, same for all callers.\n"
            "asterwise_get_tarot_three_card_spread — positional read with named positions and meanings.\n"
            "asterwise_get_tarot_celtic_cross — 10-card positional spread."
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
            "Past / Present / Future spread. Draws 3 unique cards using cryptographic randomness "
            "and assigns each to a named positional slot with an interpretive context.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "The three-card spread is the most widely used tarot layout. Position 1 (past) shows "
            "what led to the current situation. Position 2 (present) shows current energy and the "
            "core issue. Position 3 (future) shows the likely outcome if current energy continues. "
            "Each card returns position, position_meaning, and active_meaning — the complete "
            "interpretive context is included; callers do not need external position tables.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone reading.\n"
            "AFTER: asterwise_get_tarot_celtic_cross — for deeper 10-position analysis of same question.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "allow_reversed (bool, default false) — Each card independently has 50% reversal chance.\n"
            "question (optional string, max 500 chars) — The question being asked.\n"
            "  Setting a question is strongly recommended for coherent readings.\n"
            "  Example: 'What should I focus on in my career this month?'\n"
            "  The question is echoed in the response but does not affect card selection.\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.spread_type (string — 'three_card')\n"
            "data.positions[] — 3 objects in order [past, present, future]:\n"
            "  card — full card object\n"
            "  is_reversed (bool)\n"
            "  position (string — 'past'|'present'|'future')\n"
            "  position_meaning (string — what this position represents in the spread)\n"
            "  active_meaning (string — orientation-appropriate card interpretation)\n"
            "  active_keywords[] (string array)\n"
            "data.question (string or null — echoed)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — full spread object.\n"
            "response_format=markdown — formatted three-card reading.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP — cryptographic randomness, no ephemeris.\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_draw_tarot_cards — free draw with no positional meaning.\n"
            "asterwise_get_tarot_celtic_cross — 10-card spread with comprehensive positional coverage.\n"
            "asterwise_get_tarot_yes_no — single-card binary answer, no positional structure."
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
            "Ten-card Celtic Cross spread — the most comprehensive traditional tarot layout. "
            "Draws 10 unique cards using cryptographic randomness and assigns each to one of "
            "the 10 classical Celtic Cross positions.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "The Celtic Cross examines a situation from 10 angles simultaneously:\n"
            "  Position 1 (present) — the core situation\n"
            "  Position 2 (challenge) — what crosses or complicates it\n"
            "  Position 3 (root) — unconscious foundation or distant past\n"
            "  Position 4 (past) — recent events that led here\n"
            "  Position 5 (possible_outcome) — what could happen if current energy continues\n"
            "  Position 6 (near_future) — what is coming in the next weeks\n"
            "  Position 7 (self) — how you see yourself / your attitude\n"
            "  Position 8 (external) — how others see you or environmental factors\n"
            "  Position 9 (hopes_and_fears) — what you hope for or fear\n"
            "  Position 10 (outcome) — the most likely final resolution\n"
            "All position meanings are included in the response — callers do not need external tables.\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone reading, or follow asterwise_get_tarot_three_card_spread "
            "when a more detailed examination of the same question is needed.\n"
            "AFTER: None.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "allow_reversed (bool, default false) — Each card independently has 50% reversal chance.\n"
            "question (optional string, max 500 chars) — The question or situation being examined.\n"
            "  Example: 'Should I accept the job offer in London?'\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.spread_type (string — 'celtic_cross')\n"
            "data.positions[] — 10 objects in order [present, challenge, root, past, "
            "possible_outcome, near_future, self, external, hopes_and_fears, outcome]:\n"
            "  card — full card object\n"
            "  is_reversed (bool)\n"
            "  position (string — named position key)\n"
            "  position_meaning (string — what this position represents)\n"
            "  active_meaning (string — orientation-appropriate interpretation)\n"
            "  active_keywords[] (string array)\n"
            "data.question (string or null — echoed)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — full 10-card spread object.\n"
            "response_format=markdown — formatted Celtic Cross reading.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP — cryptographic randomness, no ephemeris.\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_tarot_three_card_spread — 3 positions only; use for simpler questions.\n"
            "asterwise_draw_tarot_cards — free draw with no positional meaning.\n"
            "asterwise_get_tarot_yes_no — binary answer, not positional analysis."
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
            "Draws one card and returns a yes, no, or maybe answer with confidence level. "
            "The answer is derived from the card's built-in yes_no polarity and its orientation.\n\n"
            "SECTION: WHAT THIS TOOL COVERS\n"
            "Quick binary oracle using the classical tarot yes/no system. Each card in the "
            "Rider-Waite-Smith deck has a pre-assigned polarity (yes/no/maybe). Reversal "
            "introduces uncertainty — a yes-polarity card reversed becomes maybe rather than no. "
            "This allows nuanced answers: strong yes, leaning toward yes, leaning toward no, "
            "strong no, or genuinely unclear.\n\n"
            "Answer logic (exact):\n"
            "  yes-polarity card + upright → answer='yes', confidence='strong'\n"
            "  yes-polarity card + reversed → answer='maybe', confidence='leaning'\n"
            "  no-polarity card + upright → answer='no', confidence='strong'\n"
            "  no-polarity card + reversed → answer='maybe', confidence='leaning'\n"
            "  maybe-polarity card (any orientation) → answer='maybe', confidence='unclear'\n\n"
            "SECTION: WORKFLOW\n"
            "BEFORE: None — standalone.\n"
            "AFTER: asterwise_get_tarot_three_card_spread — for more context when the yes/no "
            "answer is 'maybe' or the situation needs elaboration.\n\n"
            "SECTION: INPUT CONTRACT\n"
            "allow_reversed (bool, default true) — Recommended to keep true for nuanced answers.\n"
            "  Set false only if you want strictly yes/no with no maybe results from reversal.\n"
            "question (optional string, max 500 chars) — The yes/no question being asked.\n"
            "  Example: 'Should I accept this job offer?'\n"
            "  Example: 'Will the project launch on time?'\n\n"
            "SECTION: OUTPUT CONTRACT\n"
            "data.card — full card object\n"
            "data.is_reversed (bool)\n"
            "data.answer (string — 'yes'|'no'|'maybe')\n"
            "data.confidence (string — 'strong' when card directly says yes/no; "
            "'leaning' when reversed card; 'unclear' when maybe-polarity card)\n"
            "data.active_meaning (string — orientation-appropriate interpretation)\n"
            "data.question (string or null — echoed)\n\n"
            "SECTION: RESPONSE FORMAT\n"
            "response_format=json — full yes/no result object.\n"
            "response_format=markdown — formatted oracle response.\n\n"
            "SECTION: COMPUTE CLASS\n"
            "FAST_LOOKUP — cryptographic randomness, no ephemeris.\n\n"
            "SECTION: ERROR CONTRACT\n"
            "INVALID_PARAMS (local): None.\n"
            "INTERNAL_ERROR: Any upstream API failure → MCP INTERNAL_ERROR\n\n"
            "SECTION: DO NOT CONFUSE WITH\n"
            "asterwise_get_tarot_three_card_spread — positional reading, not binary answer.\n"
            "asterwise_draw_tarot_cards — free draw without answer logic."
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
