"""Responses must stay small enough for an agent's context window."""
from __future__ import annotations

import json

from models import ResponseFormat
from runtime import dedupe_long_strings, format_tool_result, structured_markdown
from tools.dasha import _dasha_tree_md, _slim_dasha

ESSAY = ("Rahu Mahadasha extends for eighteen years and is among the most complex to navigate. " * 18).strip()
PLANETS = ["Rahu", "Jupiter", "Saturn", "Mercury", "Ketu", "Venus", "Sun", "Moon", "Mars"]


def _dasha_payload(levels: int) -> dict:
    def period(planet, depth):
        p = {"planet": planet, "start_date": "01/01/2000", "end_date": "01/01/2010",
             "start_jd": 2451544.5, "end_jd": 2455197.5, "modern_summary": ESSAY.replace("Rahu", planet)}
        p["sub"] = [period(q, depth + 1) for q in PLANETS] if depth < levels else None
        return p
    return {"success": True, "message": "success", "data": {
        "periods": [period(p, 1) for p in PLANETS],
        "interpretation": {"current_mahadasha": {"planet": "Mercury", "modern_summary": ESSAY.replace("Rahu", "Mercury"),
                                                 "favorable_results": ["a", "b"]}},
        "birth_time_provided": True}}


def test_dedupe_keeps_first_and_points_later_copies_at_it():
    payload = {"a": ESSAY, "b": {"c": ESSAY}, "short": "x" * 50, "same_short": "x" * 50}
    out = dedupe_long_strings(payload)
    assert out["a"] == ESSAY
    assert out["b"]["c"] == "(identical to a)"
    assert out["short"] == out["same_short"] == "x" * 50  # short strings untouched


def test_two_level_dasha_is_small_in_both_formats():
    payload = _dasha_payload(2)
    raw = len(json.dumps(payload))
    as_json = format_tool_result(_slim_dasha(payload), ResponseFormat.JSON, _dasha_tree_md)
    as_md = format_tool_result(_slim_dasha(payload), ResponseFormat.MARKDOWN, _dasha_tree_md)
    assert raw > 120_000, raw  # the shape that timed out in production (300 KB live)
    assert len(as_json) < 45_000, len(as_json)
    assert len(as_md) < 20_000, len(as_md)
    assert ESSAY.replace("Rahu", "Mercury") in as_md  # current-period essay rendered in full
    assert "(identical to" not in as_md
    three = _dasha_payload(3)
    assert len(json.dumps(three)) > 1_000_000
    assert len(format_tool_result(_slim_dasha(three), ResponseFormat.JSON, _dasha_tree_md)) < 130_000
    assert "Raw structure" not in as_md
    assert "Current periods" in as_md
    # every antardasha line is still present in markdown (9 x 9 "  - Planet: start → end")
    import re
    assert len(re.findall(r"^  - [A-Z][a-z]+: ", as_md, flags=re.M)) == 81


def test_markdown_renderer_handles_generic_payloads():
    md = structured_markdown("Title", {"a": 1, "b": [1, 2], "c": {"d": None}})
    assert md.startswith("## Title")


def test_muhurta_windows_are_shown_without_the_legacy_fields():
    from tools.panchanga import _clean_muhurta

    raw = {"success": True, "data": {"top_windows": [{
        "date": "2026-11-24", "start": "03:05", "end": "05:08", "score": 85,
        "choghadiya": "Labh", "choghadiya_type": "auspicious", "yoga": "Shiva", "yoga_number": 20,
        "vara": "Budhvar", "vara_number": 4, "vara_lord": "Mercury", "tithi": "Pratipada",
        "tithi_number": 16, "paksha": "Krishna", "reason": "x", "is_rahu_kaal": False,
        "start_at": "2026-11-25T03:05:00+05:30", "end_at": "2026-11-25T05:08:00+05:30",
        "civil_date": "2026-11-25", "panchanga_day": "2026-11-24",
    }]}}
    w = _clean_muhurta(raw)["data"]["top_windows"][0]
    assert "date" not in w and "start" not in w and "end" not in w and "reason" not in w
    assert w["start_at"] == "2026-11-25T03:05:00+05:30"
    assert w["civil_date"] == "2026-11-25" and w["panchanga_day"] == "2026-11-24"
    assert w["tithi"] == {"number": 16, "name": "Pratipada", "paksha": "Krishna"}
    assert w["vara"] == {"number": 4, "name": "Budhvar", "lord": "Mercury"}
    assert w["yoga"] == {"number": 20, "name": "Shiva"}
    assert w["choghadiya"] == "Labh"
