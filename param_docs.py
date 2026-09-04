"""Parameter descriptions injected into tool input schemas.

Most tools take plain scalars whose meaning is shared across the server
(dates, names, coordinates). FastMCP only emits a ``description`` for a
parameter when it is declared with ``Field(description=...)``, and MCP
directories score servers on parameter descriptions, so this module fills
every top-level property that lacks one from a single vocabulary.

``TOOL_PARAM_DESCRIPTIONS`` overrides ``PARAM_DESCRIPTIONS`` when a name
means something more specific in one tool.
"""

from __future__ import annotations

from typing import Any

_DATE = "Date in YYYY-MM-DD format."
_DATE_OPT = "Date in YYYY-MM-DD format. Defaults to today when omitted."

PARAM_DESCRIPTIONS: dict[str, str] = {
    "response_format": (
        "Output format: 'markdown' (default) for a readable report, "
        "or 'json' for the raw structured payload."
    ),
    "date": _DATE_OPT,
    "target_date": _DATE_OPT,
    "start_date": "Start of the window, YYYY-MM-DD. Defaults to today when omitted.",
    "from_date": "Start of the date range, YYYY-MM-DD (inclusive).",
    "to_date": "End of the date range, YYYY-MM-DD (inclusive).",
    "after_date": (
        "Find the first occurrence after this date, YYYY-MM-DD. "
        "Defaults to today when omitted."
    ),
    "birth_date": "Date of birth, YYYY-MM-DD.",
    "name": "Person's full name as commonly written; letters are converted to numerology values.",
    "year": "Four-digit calendar year, e.g. 2026. Defaults to the current year when omitted.",
    "month": "Month number 1-12. Defaults to the current month when omitted.",
    "day": "Day of the month 1-31. Defaults to today when omitted.",
    "planet": "Planet name in English, e.g. 'Jupiter', 'Saturn', 'Rahu'.",
    "allow_reversed": "Whether cards may be drawn reversed (upside down).",
    "question": "The question being asked; it shapes the reading's interpretation.",
    "levels": (
        "Depth of the dasha tree: 1 returns major periods only, each extra "
        "level adds the next sub-period layer."
    ),
    "location": (
        "Place name, e.g. 'Chennai, India'. Alternative to giving latitude, "
        "longitude and timezone."
    ),
    "latitude": "Latitude in decimal degrees, north positive (e.g. 13.08).",
    "longitude": "Longitude in decimal degrees, east positive (e.g. 80.27).",
    "lat": "Latitude in decimal degrees, north positive (e.g. 13.08).",
    "lon": "Longitude in decimal degrees, east positive (e.g. 80.27).",
    "timezone": "IANA time zone name, e.g. 'Asia/Kolkata'.",
    "period": "Horoscope period: daily, weekly, monthly or yearly.",
    "include_interpretation": "Include a written interpretation alongside the chart data.",
    "chart_type": "Divisional chart to return, D1 to D60. Omit to return all 16 charts.",
    "nakshatra_name": "Nakshatra name, e.g. 'Rohini' or 'Uttara Phalguni'.",
    "house_number": "House number 1-12. Omit to cover all twelve houses.",
    "activity": (
        "Activity to find an auspicious time for, e.g. 'marriage', 'travel', "
        "'business opening'."
    ),
    "days": "Number of consecutive days to include, starting from the target date.",
    "person1_name": "First person's full name.",
    "person1_date": "First person's date of birth, YYYY-MM-DD.",
    "person2_name": "Second person's full name.",
    "person2_date": "Second person's date of birth, YYYY-MM-DD.",
    "mobile_number": "Mobile number to analyse; digits only, country code optional.",
    "vehicle_number": "Vehicle registration number, e.g. 'DL01AB1234'.",
    "business_name": "Business or brand name to analyse.",
    "zodiac_sign": "Zodiac sign, e.g. 'Leo'.",
    "chakra": "Chakra to focus on, e.g. 'heart' or 'third eye'.",
    "intention": "Purpose for the recommendation, e.g. 'protection', 'focus', 'love'.",
    "limit": "Maximum number of results to return.",
    "category": "Category to filter by. Omit to include every category.",
    "moon_sign": "Vedic moon sign (rashi), e.g. 'Vrishabha' or 'Taurus'.",
    "sun_sign": "Western sun sign, e.g. 'Aries'.",
    "sign1": "First zodiac sign, e.g. 'Aries'.",
    "sign2": "Second zodiac sign, e.g. 'Libra'.",
    "suit": "Minor arcana suit: wands, cups, swords or pentacles.",
    "count": "Number of cards to draw.",
    "card_id": "Tarot card identifier in kebab-case, e.g. 'the-fool' or 'ace-of-wands'.",
    "number": "Number to interpret.",
    "positions": (
        "Planet positions to compare: a mapping of planet name to ecliptic "
        "longitude in degrees (0-360)."
    ),
}

TOOL_PARAM_DESCRIPTIONS: dict[tuple[str, str], str] = {
    ("asterwise_get_tamil_panchanga", "date"): "Date for the Tamil panchanga, YYYY-MM-DD.",
    ("asterwise_get_ayanamsha", "date"): (
        "Date to compute the ayanamsha for, YYYY-MM-DD. Defaults to today."
    ),
    ("asterwise_get_western_moon_phase", "date"): (
        "Date for the moon phase, YYYY-MM-DD. Defaults to today."
    ),
    ("asterwise_get_varshaphal", "year"): (
        "Year of the solar return to compute, four digits, e.g. 2026."
    ),
    ("asterwise_get_angel_number_personal", "name"): (
        "Person's name, used to personalise the angel number reading."
    ),
    ("asterwise_get_western_planetary_return", "planet"): (
        "Planet whose return to compute, e.g. 'Jupiter' or 'Saturn'."
    ),
    ("asterwise_get_crystal_by_planet", "planet"): (
        "Planet to find crystals for, e.g. 'Venus' or 'Saturn'."
    ),
    ("asterwise_get_number_meaning", "number"): (
        "Number to interpret: 1-9, or a master number 11, 22 or 33."
    ),
    ("asterwise_get_angel_number", "number"): (
        "Angel number sequence as seen, e.g. '111' or '1234'."
    ),
    ("asterwise_get_dream_symbols", "category"): (
        "Symbol category to filter by, e.g. 'animals' or 'water'. Omit for all."
    ),
    ("asterwise_get_horoscope", "period"): (
        "Horoscope period: daily, weekly, monthly or yearly."
    ),
    ("asterwise_get_muhurta", "from_date"): (
        "Start of the search window for auspicious times, YYYY-MM-DD."
    ),
    ("asterwise_get_muhurta", "to_date"): (
        "End of the search window for auspicious times, YYYY-MM-DD."
    ),
    ("asterwise_get_transits", "from_date"): (
        "Start of the window to list ingress and station events, YYYY-MM-DD."
    ),
    ("asterwise_get_transits", "to_date"): (
        "End of the window to list ingress and station events, YYYY-MM-DD."
    ),
    ("asterwise_get_biorhythm", "target_date"): (
        "Date to chart the cycles for, YYYY-MM-DD. Defaults to today."
    ),
    ("asterwise_get_tarot_yes_no", "question"): "The yes/no question being asked.",
    ("asterwise_get_dasha", "levels"): (
        "Depth of the Vimshottari tree, 1-5: 1 = Mahadasha only, 2 adds Antardasha "
        "(default), 3 Pratyantar, 4 Sookshma, 5 Prana (much larger payload)."
    ),
}


def describe_parameters(mcp: Any) -> list[tuple[str, str]]:
    """Fill missing top-level parameter descriptions on every registered tool.

    Returns the ``(tool, parameter)`` pairs that are still undescribed so
    the caller (and the test suite) can flag vocabulary gaps.
    """
    from fastmcp.tools import Tool

    missing: list[tuple[str, str]] = []
    for component in mcp._local_provider._components.values():
        if not isinstance(component, Tool):
            continue
        props = (component.parameters or {}).get("properties") or {}
        for param, schema in props.items():
            if not isinstance(schema, dict) or schema.get("description"):
                continue
            text = TOOL_PARAM_DESCRIPTIONS.get((component.name, param)) or PARAM_DESCRIPTIONS.get(param)
            if text:
                schema["description"] = text
            else:
                missing.append((component.name, param))
    return missing
