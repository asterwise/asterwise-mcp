"""Parameter descriptions injected into tool input schemas.

Most tools take plain scalars whose meaning is shared across the server
(dates, names, coordinates). FastMCP only emits a ``description`` for a
parameter when it is declared with ``Field(description=...)``, and MCP
directories score servers on parameter descriptions, so this module fills
every top-level property that lacks one from a single vocabulary.

``TOOL_PARAM_DESCRIPTIONS`` overrides ``PARAM_DESCRIPTIONS`` when a name
means something more specific in one tool.

The shared vocabulary only says what a parameter IS. What a tool DOES with
it (a default when omitted, whether a name is used at all) differs between
endpoints, so it goes in TOOL_PARAM_DESCRIPTIONS, checked against the API.
A shared "Defaults to today when omitted" once told agents that personal
cycles fills in the day (it leaves Personal Day out) and that personal year
reads the name (it ignores it). tests/test_param_descriptions.py keeps
behaviour claims out of the shared entries.
"""

from __future__ import annotations

import re
from typing import Any

_DATE = "Date in YYYY-MM-DD format."

PARAM_DESCRIPTIONS: dict[str, str] = {
    "response_format": (
        "Output format: 'markdown' (default) for a readable report, "
        "or 'json' for the raw structured payload."
    ),
    "date": _DATE,
    "target_date": _DATE,
    "start_date": "Start of the window, YYYY-MM-DD.",
    "from_date": "Start of the date range, YYYY-MM-DD (inclusive).",
    "to_date": "End of the date range, YYYY-MM-DD (inclusive).",
    "after_date": "Find the first occurrence after this date, YYYY-MM-DD.",
    "birth_date": "Date of birth, YYYY-MM-DD.",
    "name": "Person's full name as commonly written.",
    "year": "Four-digit calendar year, e.g. 2026.",
    "month": "Month number 1-12.",
    "day": "Day of the month 1-31.",
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
    ("asterwise_check_mobile_number", "name"): (
        "Not used: the analysis depends only on the digits. Omit it; "
        "it is accepted only so older calls keep working."
    ),
    ("asterwise_check_mobile_number", "date"): (
        "Not used: the analysis depends only on the digits. Omit it; "
        "it is accepted only so older calls keep working."
    ),
    ("asterwise_check_vehicle_number", "name"): (
        "Not used: the analysis depends only on the digits. Omit it; "
        "it is accepted only so older calls keep working."
    ),
    ("asterwise_check_vehicle_number", "date"): (
        "Not used: the analysis depends only on the digits. Omit it; "
        "it is accepted only so older calls keep working."
    ),
    ("asterwise_get_business_name_analysis", "date"): (
        "Not used: the analysis depends only on the business name. Omit it; "
        "it is accepted only so older calls keep working."
    ),
    ("asterwise_get_tamil_panchanga", "date"): "Date for the Tamil panchanga, YYYY-MM-DD.",
    ("asterwise_get_ayanamsha", "date"): (
        "Date to compute the ayanamsha for, YYYY-MM-DD. Defaults to today."
    ),
    ("asterwise_get_western_moon_phase", "date"): (
        "Date for the moon phase, YYYY-MM-DD (years 1-3000). Defaults to today (UTC)."
    ),
    ("asterwise_get_western_moon_calendar", "year"): (
        "Four-digit year, 1-3000. Defaults to the current year (UTC)."
    ),
    ("asterwise_get_western_moon_calendar", "month"): (
        "Month number 1-12. Defaults to the current month (UTC)."
    ),
    ("asterwise_get_varshaphal", "year"): (
        "Varshaphal year, four digits, e.g. 2026: the solar return nearest the birthday "
        "in that year (in UTC it can fall a day either side, or on 31 Dec for a 1 Jan "
        "birthday). Must not be before the birth year."
    ),
    ("asterwise_get_varshaphal_saham", "year"): (
        "Varshaphal year, four digits, e.g. 2026: the solar return nearest the birthday "
        "in that year (in UTC it can fall a day either side, or on 31 Dec for a 1 Jan "
        "birthday). Must not be before the birth year."
    ),
    ("asterwise_get_varshaphal_harsha_bala", "year"): (
        "Varshaphal year, four digits, e.g. 2026: the solar return nearest the birthday "
        "in that year (in UTC it can fall a day either side, or on 31 Dec for a 1 Jan "
        "birthday). Must not be before the birth year."
    ),
    ("asterwise_get_angel_number_personal", "name"): (
        "Person's name, used to personalise the angel number reading."
    ),
    ("asterwise_get_western_planetary_return", "planet"): (
        "Planet whose return to compute, e.g. 'Jupiter' or 'Saturn'."
    ),
    ("asterwise_get_crystal", "name"): (
        "Crystal slug or display name, e.g. 'amethyst', 'blue-sapphire', "
        "'Cat's Eye Chrysoberyl'."
    ),
    ("asterwise_get_dream_symbol", "name"): (
        "Dream symbol slug or display name, e.g. 'snake', 'eagle', "
        "'childhood-home', 'lotus'."
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
        "Symbol category: animals, nature, people, places, objects, actions, body or abstract. Omit for all 500 symbols."
    ),
    ("asterwise_get_horoscope", "period"): (
        "Horoscope period: daily, weekly, monthly or yearly."
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
    ("asterwise_get_kp_ruling_planets", "target_date"): (
        "Local date of the moment to judge, YYYY-MM-DD. Without target_time, "
        "12:00 local is used. Omit both date and time for the current instant."
    ),
    ("asterwise_get_kp_ruling_planets", "target_time"): (
        "Local time of the moment to judge, HH:MM (24-hour). Without target_date, "
        "that time today. Omit both date and time for the current instant."
    ),
    ("asterwise_get_kp_ruling_planets", "target_timezone"): (
        "IANA time zone for target_date and target_time, e.g. 'Asia/Kolkata'. "
        "Defaults to the zone at lat/lon."
    ),
    ("asterwise_get_angel_number_today", "date"): (
        "Date to compute the angel number for, YYYY-MM-DD. Overrides timezone. "
        "Omit for today."
    ),
    ("asterwise_get_angel_number_today", "timezone"): (
        "IANA time zone whose current date counts as today, e.g. 'Asia/Kolkata'. "
        "Defaults to UTC; ignored when date is given."
    ),
    ("asterwise_check_mobile_number", "country"): (
        "Country of the number as ISO 3166 alpha-2, e.g. 'IN', 'US', 'CN'. Used only "
        "when the number has no '+'/'00' prefix: it is then read as dialled in that "
        "country and the country code is left out of the sum."
    ),
    ("asterwise_get_tarot_card_of_the_day", "timezone"): (
        "IANA time zone (or ±HH:MM) whose current date counts as today, e.g. "
        "'Asia/Kolkata'. Defaults to UTC; ignored when date is given."
    ),
    ("asterwise_get_tarot_card_of_the_day", "date"): (
        "Date to get the card for, YYYY-MM-DD. Defaults to today's date in UTC, "
        "or in timezone. Overrides timezone."
    ),
    ("asterwise_get_char_dasha", "cycles"): (
        "Char Dasha cycles to return, 1-3 (default 1). Every further cycle repeats the "
        "first cycle's signs, order and years (K.N. Rao)."
    ),
    ("asterwise_get_ashtottari_dasha", "levels"): (
        "Depth of the Ashtottari tree, 1-5: 1 = Mahadasha only, 2 adds Antardasha "
        "(default), 3 Pratyantar, 4 Sookshma, 5 Prana."
    ),
}

# Name-based numerology: the API reduces the name's letters.
_NUMEROLOGY_NAME = (
    "Person's full name as commonly written; its letters are converted to numerology values."
)
for _tool in (
    "asterwise_get_balance_number", "asterwise_get_chaldean_numerology",
    "asterwise_get_expression_number", "asterwise_get_karmic_lessons",
    "asterwise_get_lucky_numbers", "asterwise_get_maturity_number",
    "asterwise_get_name_correction", "asterwise_get_numerology_profile",
    "asterwise_get_personality_number", "asterwise_get_soul_urge_number",
):
    TOOL_PARAM_DESCRIPTIONS[(_tool, "name")] = _NUMEROLOGY_NAME

# Defaults as the API applies them. The API servers run in UTC, so a plain
# "today" there is the UTC date.
TOOL_PARAM_DESCRIPTIONS.update({
    ("asterwise_get_numerology_compatibility", "person1_name"): (
        "First person's full name. The API requires it, but it does not change the "
        "score: compatibility compares the two Life Path numbers from the birth dates."
    ),
    ("asterwise_get_numerology_compatibility", "person2_name"): (
        "Second person's full name. The API requires it, but it does not change the "
        "score: compatibility compares the two Life Path numbers from the birth dates."
    ),
    ("asterwise_get_personal_year", "name"): (
        "Not used: the personal year depends only on the birth date. Omit it; "
        "it is accepted only so older calls keep working."
    ),
    ("asterwise_get_personal_cycles", "year"): (
        "Four-digit target year, e.g. 2026. Defaults to the current year (UTC)."
    ),
    ("asterwise_get_personal_cycles", "month"): (
        "Target month 1-12. Defaults to the current month (UTC)."
    ),
    ("asterwise_get_personal_cycles", "day"): (
        "Target day of the month 1-31. Personal Day is returned only when day is given; "
        "omit it to get Personal Year and Personal Month only."
    ),
    ("asterwise_get_gochar", "target_date"): (
        "Date to compute transits for, YYYY-MM-DD (at 12:00 India time). "
        "Defaults to today in India (Asia/Kolkata)."
    ),
    ("asterwise_get_nakshatra_prediction", "target_date"): (
        "Date of the prediction, YYYY-MM-DD. Defaults to today in the birth time zone."
    ),
    ("asterwise_get_western_lunar_return", "after_date"): (
        "Find the first lunar return after this date, YYYY-MM-DD. Defaults to today (UTC)."
    ),
    ("asterwise_get_western_planetary_return", "after_date"): (
        "Find the first return after this date, YYYY-MM-DD. Defaults to today (UTC)."
    ),
    ("asterwise_get_western_secondary_progressions", "target_date"): (
        "Date to progress the chart to, YYYY-MM-DD. Defaults to today (UTC)."
    ),
    ("asterwise_get_western_solar_arc", "target_date"): (
        "Date to direct the chart to, YYYY-MM-DD. Defaults to today (UTC)."
    ),
    ("asterwise_get_western_transits_daily", "start_date"): (
        "Day to compute transits for, YYYY-MM-DD. Defaults to today (UTC)."
    ),
    ("asterwise_get_western_transits_weekly", "start_date"): (
        "First day of the 7-day window, YYYY-MM-DD. Defaults to today (UTC)."
    ),
    ("asterwise_get_western_transits_monthly", "start_date"): (
        "First day of the 30-day window, YYYY-MM-DD. Defaults to today (UTC)."
    ),
})


def _described(schema: Any, defs: dict, seen: frozenset[str] = frozenset()) -> bool:
    """True when ``schema`` carries a description, directly or by reference.

    A parameter typed as a model (``{"$ref": "#/$defs/BirthData"}``) has no
    description of its own; the text lives on the referenced definition and
    is inlined in the schema clients receive. Treating those as undescribed
    produced a startup warning for 55 parameters that are in fact documented.
    """
    if not isinstance(schema, dict):
        return False
    if str(schema.get("description", "")).strip():
        return True

    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/$defs/"):
        name = ref.rsplit("/", 1)[-1]
        if name not in seen:  # guard against recursive models
            return _described(defs.get(name), defs, seen | {name})

    for keyword in ("anyOf", "allOf", "oneOf"):
        variants = schema.get(keyword)
        if isinstance(variants, list) and any(
            _described(v, defs, seen) for v in variants
        ):
            return True
    return False


_DEFAULT_CLAUSE = re.compile(
    r"\s*(?:Defaults?\s+to\s+[^.]*\.|Omit\s+(?:to|if|when)\s+[^.]*\.)"
)


def _fit_to_schema(text: str, *, required: bool) -> str:
    """Drop any promise of a default from a parameter the schema requires.

    The shared vocabulary describes the common case, where these parameters
    are optional. On tools that require them, keeping "Defaults to today when
    omitted" tells an agent to omit a field the API rejects.
    """
    if not required:
        return text
    return _DEFAULT_CLAUSE.sub("", text).strip()


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
        parameters = component.parameters or {}
        defs = parameters.get("$defs") or {}
        props = parameters.get("properties") or {}
        required = set(parameters.get("required") or ())
        for param, schema in props.items():
            if not isinstance(schema, dict) or _described(schema, defs):
                continue
            text = TOOL_PARAM_DESCRIPTIONS.get((component.name, param)) or PARAM_DESCRIPTIONS.get(param)
            if text:
                schema["description"] = _fit_to_schema(text, required=param in required)
            else:
                missing.append((component.name, param))
    return missing
