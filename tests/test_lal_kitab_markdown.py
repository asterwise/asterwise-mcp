"""Lal Kitab markdown is a readable report, not a dump of the JSON keys."""

from tools.natal import _lk_chart_md, _lk_remedies_md

CHART = {"success": True, "data": {
    "ayanamsa": "lahiri", "birth_time_provided": False,
    "ascendant": {"longitude": 99.88, "rashi_index": 3, "rashi": "Karka"},
    "planets": {"Sun": {"lk_house": 11, "rashi": "Vrishabha", "pucca_ghar": False, "uchcha": False,
                        "neecha": False, "effect": "doubtful",
                        "malefic_reasons": ["house 11 is owned by its enemy Saturn"]}},
    "rin_analysis": {"rin_remedies": [{"name": "Debt to mother (Matri rin)", "found": [{"planet": "Ketu", "house": 4}],
                                       "remedy": "Silver in a river.", "source": "Lal Kitab tradition"}],
                     "not_evaluated": "Two checks are not computed."},
}}

REMEDIES = {"success": True, "data": {
    "birth_time_provided": True,
    "remedies": [{"planet": "Sun", "lk_house": 11, "malefic_reasons": ["house 11 is owned by its enemy Saturn"],
                  "remedies": [{"type": "donation", "action": "Give wheat.", "condition": "Saturn in 3"}]}],
    "not_remediable": [{"planet": "Saturn", "lk_house": 1, "reasons": ["debilitated in house 1"]}],
    "rin_remedies": [], "sources": ["Lal Kitab tradition"],
}}


def test_chart_markdown_is_a_table_with_time_warning():
    md = _lk_chart_md(CHART)
    assert "| Sun | 11 | Vrishabha |" in md
    assert "sunrise chart" in md
    assert "Matri rin" in md and "Ketu in 4" in md
    assert "Item 1" not in md and "Success" not in md


def test_remedies_markdown_shows_condition_without_book_page():
    md = _lk_remedies_md(REMEDIES)
    assert "### Sun in house 11" in md
    assert "Give wheat. (when: Saturn in 3)" in md
    assert "p." not in md.split("Give wheat.")[1].splitlines()[0]
    assert "Saturn in house 1" in md
    assert "Item 1" not in md and "sunrise chart" not in md


def test_tropical_is_refused_before_the_api_call():
    import pytest
    from mcp.shared.exceptions import McpError
    from models import BirthData
    from tools.natal import _lk_reject_tropical

    with pytest.raises(McpError, match="sidereal"):
        _lk_reject_tropical(BirthData(date="2000-08-25", time="12:00", lat=28.6, lon=77.2, ayanamsa="tropical"))
    for a in ("lahiri", "raman", "kp"):
        _lk_reject_tropical(BirthData(date="2000-08-25", time="12:00", lat=28.6, lon=77.2, ayanamsa=a))
