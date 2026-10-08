"""Full descriptions for the panchanga-family tools (compacted by runtime.compact_description)."""

from __future__ import annotations

PANCHANGA = """Panchanga for one date at a location: the limbs at sunrise plus the whole panchanga day (sunrise to next sunrise) with every tithi, nakshatra, yoga and karana active in it, each with ISO start and end times and kshaya/vriddhi flags; sunrise, sunset, moonrise and moonset; Sun and Moon rashi; lunar month (amanta and purnimanta, with Adhik months); Vikram, Shaka and Gujarati samvat; ritu and ayana; and the day's timings (Rahu Kaal, Gulika, Yamaganda, Abhijit, Brahma Muhurta, Durmuhurta, Varjyam, Amrit Kaal, Bhadra with residence, Panchaka, Pradosh, Nishita).

SECTION: WHAT THIS TOOL COVERS
The top-level tithi, vara, nakshatra, yoga and karana are the limbs at sunrise. A tithi that starts after sunrise and ends before the next one (kshaya) appears in data.tithis flagged is_kshaya; a tithi that holds two sunrises is flagged is_vriddhi on both days. Times are ISO 8601 local time with offset. data.yoga is the Panchanga Yoga (Sun+Moon), unrelated to natal yogas.

SECTION: WORKFLOW
BEFORE: asterwise_geocode — when you only have a place name.
AFTER: asterwise_get_muhurta — to find auspicious windows across a date range; asterwise_get_festival_calendar — for the festivals and vrats of the year.

SECTION: INPUT CONTRACT
location.date is YYYY-MM-DD; location.lat, location.lon and location.timezone (IANA) give the place. Dates 1800-2099.

SECTION: OUTPUT CONTRACT
data.tithi, data.vara, data.nakshatra, data.yoga, data.karana: limbs at sunrise (end_time in UTC).
data.date, data.sunrise, data.sunset, data.next_sunrise, data.moonrise (null if none), data.moonset (null if none): ISO local.
data.tithis[], data.nakshatras[] (with padas[]), data.yogas[], data.karanas[]: number/index, name, start, end, at_sunrise, is_kshaya, is_vriddhi.
data.sun_rashi[], data.moon_rashi[], data.sun_nakshatra[]: name, start, end.
data.paksha; data.masa.amanta / data.masa.purnimanta: name, display_name, is_adhik.
data.samvat: vikram, shaka, gujarati, samvatsara. data.ritu: vedic, drik. data.ayana: vedic, drik.
data.timings: brahma_muhurta, pratah_sandhya, abhijit (null on Wednesday), vijaya_muhurta, godhuli_muhurta, sayahna_sandhya, nishita_muhurta, madhyahna, pradosh, rahu_kaal, gulika_kaal, yamaganda_kaal, durmuhurta[], varjyam[], amrit_kaal[], bhadra[] (residence), panchaka[], day_parts.

SECTION: ERROR CONTRACT
INVALID_PARAMS (local): bad date or coordinates. INTERNAL_ERROR: upstream failure, including polar dates without sunrise.

SECTION: DO NOT CONFUSE WITH
asterwise_get_yogas — natal chart yogas, not the Panchanga Sun–Moon yoga.
asterwise_get_panchanga_calendar — one row per day for a whole month.
asterwise_get_tamil_panchanga — Tamil month and Rahu Kalam/Yamagandam/Kuligai only."""

PANCHANGA_CALENDAR = """Panchanga for every day of a month at a location: each day's sunrise tithi, vara, nakshatra, yoga, karana and Rahu Kaal, plus sunrise, sunset, moonrise, moonset, paksha, lunar month (amanta and purnimanta, with Adhik months), Bhadra windows, and every tithi, nakshatra, yoga and karana active that day with ISO start and end times.

SECTION: WHAT THIS TOOL COVERS
A kshaya tithi (one that no sunrise touches) appears on the day it runs, flagged is_kshaya; a tithi that holds two sunrises is flagged is_vriddhi on both days, so no tithi goes missing and repeats are explained.

SECTION: WORKFLOW
BEFORE: asterwise_geocode — when you only have a place name.
AFTER: asterwise_get_panchanga — full timings for one chosen day.

SECTION: INPUT CONTRACT
calendar.year 1900-2100, calendar.month 1-12, calendar.lat, calendar.lon, calendar.timezone (IANA; default Asia/Kolkata — set it for places outside India).

SECTION: OUTPUT CONTRACT
data.days[]: date, tithi, vara, nakshatra, yoga, karana (sunrise limbs), rahu_kaal (HH:MM), sunrise, sunset, moonrise, moonset, paksha, masa, tithis[], nakshatras[], yogas[], karanas[] (start, end, at_sunrise, is_kshaya, is_vriddhi), bhadra[].

SECTION: ERROR CONTRACT
INVALID_PARAMS (local): year or month out of range. INTERNAL_ERROR: upstream failure.

SECTION: DO NOT CONFUSE WITH
asterwise_get_panchanga — one day with all timings.
asterwise_get_festival_calendar — festivals and vrats rather than daily limbs."""

MUHURTA = """Finds auspicious time windows for an activity between two dates (up to a year) at a location, with exact ISO start and end times. Activities: marriage, griha_pravesh, business, travel, naming_ceremony, vehicle_purchase, property_purchase, mundan, annaprashan, upanayana, vidyarambha. Applies each activity's nakshatra, tithi and weekday rules, seasonal bans (Chaturmas, Adhik Maas, Pitru Paksha, Kharmas, Holashtak, Guru/Shukra asta, Panchaka), and avoids Rahu Kaal, Yamaganda, Gulika, Durmuhurta, Varjyam and Bhadra; scores 0-100 with reasons, and excluded_minutes explains an empty result.

SECTION: WHAT THIS TOOL COVERS
The range is cut at every change of tithi, nakshatra, yoga, karana, lagna, sunrise and sunset and at the edges of Rahu Kaal, Yamaganda, Gulika, Durmuhurta, Varjyam and Bhadra. A moment is ruled out when the season bars the activity (Chaturmas, Adhik Maas, Pitru Paksha, Kharmas, Holashtak, Guru or Shukra asta, Panchaka — per activity), when its nakshatra, tithi or weekday is not one the activity allows (e.g. no Pushya, Tuesday, Saturday or Rikta tithi for marriage), or when it falls in an inauspicious period. Survivors are scored 0-100 with reasons and cautions; excluded_minutes says why the rest was ruled out (so an empty result in Chaturmas is explained). Participants add Tarabala and Chandrabala.

SECTION: WORKFLOW
BEFORE: asterwise_geocode — when you only have a place name.
AFTER: asterwise_get_panchanga — full timings for a chosen window's day.

SECTION: INPUT CONTRACT
request.activity (enum above), request.from_date and request.to_date (YYYY-MM-DD, at most 366 days apart), request.lat, request.lon, request.timezone (IANA). Optional: top_n (1-50, default 5), max_windows_per_day (default 1, so results spread across dates), participants (up to two, each with nakshatra and optional moon_rashi, or birth_date, birth_time, birth_lat, birth_lon, birth_timezone).

SECTION: OUTPUT CONTRACT
data.criteria: nakshatras, tithis, weekdays, preferred_lagnas, avoided_seasons, avoided_periods, daytime_only.
data.excluded_minutes: minutes ruled out by reason. data.total_windows_found.
data.top_windows[]: start_at, end_at (ISO local), duration_minutes, civil_date (date of start), panchanga_day (sunrise date; differs after midnight), score, grade, tithi {number, name, paksha}, nakshatra, yoga, karana, vara {number, name, lord}, lagna (for lagna-based activities), masa, choghadiya, is_abhijit, is_amrita_siddhi, is_sarvartha_siddhi, is_guru_pushya, is_ravi_pushya, reasons[], cautions[], tarabala[] and chandrabala[] (with participants).

SECTION: ERROR CONTRACT
INVALID_PARAMS (local): unknown activity, bad dates, range over 366 days, participant without nakshatra or birth details. INTERNAL_ERROR: upstream failure.

SECTION: DO NOT CONFUSE WITH
asterwise_get_choghadiya — the sixteen slots of one day, not a ranked search.
asterwise_get_panchanga — one day's limbs and timings."""

FESTIVAL_CALENDAR = """Hindu festivals, vrats, sankrantis, eclipses and periods for a year at a location. Each lunar festival is fixed by its lunar month (amanta, with Adhik months found from new moons and sankrantis), its tithi, and the part of the day the tithi must hold (sunrise, forenoon, Madhyahna, Aparahna, Pradosh, Nishita, moonrise), with the classical tie-breaks when a tithi spans two days, Bhadra rules for Holika Dahan and Raksha Bandhan, and the Smarta Ekadashi rule. Checked against Drik Panchang (New Delhi).

SECTION: WHAT THIS TOOL COVERS
Categories: festival (about 50: Diwali, Holi, Dussehra, Janmashtami, Karva Chauth, Govardhan, Chhath, Chaitra Navratri ...), vrat (every Ekadashi, Pradosh, Sankashti Chaturthi, Masik Shivaratri, Purnima, the Purnima vrat day (purnima_vrat: Purnima at moonrise, else sunrise), Amavasya), sankranti (12 solar ingresses), eclipse (with local visibility and contact times), period (Adhik Maas, Chaturmas, Pitru Paksha, both Navratris, Holashtak, Kharmas). Dates depend on the location's sunrise and sunset.

SECTION: WORKFLOW
BEFORE: asterwise_geocode — when you only have a place name.
AFTER: asterwise_get_panchanga — the day's limbs and timings for a festival date.

SECTION: INPUT CONTRACT
year (1900-2100), lat, lon, timezone (IANA, default Asia/Kolkata). categories: optional list of festival, vrat, sankranti, eclipse, period; the default is ["festival"] (about 50 named festivals). Add "vrat" for every Ekadashi, Pradosh, Sankashti, Purnima and Amavasya, "period" for Adhik Maas, Pitru Paksha and Chaturmas, "eclipse" for eclipses.

SECTION: OUTPUT CONTRACT
data.festivals[] sorted by date: id, name, date, end_date (periods), type (solar, tithi, eclipse), category, description (the rule used), significance, masa {amanta, purnimanta, is_adhik}, paksha, tithi {number, name, start, end}, rule (part of the day that decided, or day_after for Holi, which has no observance_window), observance_window {start, end} (puja window), note (when Bhadra or a short tithi moved the date), sankranti {rashi, moment}, eclipse {body, kind, greatest, visible_here, local}.

SECTION: ERROR CONTRACT
INVALID_PARAMS (local): bad year or coordinates, unknown category. INTERNAL_ERROR: upstream failure.

SECTION: DO NOT CONFUSE WITH
asterwise_get_panchanga_calendar — daily limbs for a month, not festivals.
asterwise_get_muhurta — auspicious windows for an activity, not festival dates."""

TAMIL_PANCHANGA = """Tamil Panchanga for a date and location: Rahu Kalam, Yamagandam and Kuligai (Gulika), Nalla Neram (daytime windows free of those periods), and the Tamil solar month from the Sun's sidereal sign at sunrise.

SECTION: WHAT THIS TOOL COVERS
The three periods are eighths of the daytime from sunrise to sunset by the Tamil weekday table. The emagandam key is the Tamil spelling of Yamagandam and repeats the same period. For tithi, nakshatra and the full timings use asterwise_get_panchanga.

SECTION: WORKFLOW
BEFORE: asterwise_geocode — when you only have a place name.
AFTER: asterwise_get_panchanga — the day's limbs and other timings.

SECTION: INPUT CONTRACT
date (YYYY-MM-DD), lat, lon, timezone (IANA, default Asia/Kolkata).

SECTION: OUTPUT CONTRACT
data.date, data.sunrise, data.sunset (HH:MM local), data.tamil_month, data.rahu_kalam, data.yamagandam, data.kuligai, data.emagandam (same as yamagandam): start, end, duration_minutes, is_active. data.nalla_neram[]: start, end.

SECTION: ERROR CONTRACT
INVALID_PARAMS (local): bad date or coordinates. INTERNAL_ERROR: upstream failure.

SECTION: DO NOT CONFUSE WITH
asterwise_get_rahu_kaal — the same three periods without the Tamil month or Nalla Neram.
asterwise_get_panchanga — the full panchanga day."""

NAKSHATRA_PREDICTION = """Personal daily prediction from Tarabala and Chandrabala for the day at the birth place (sunrise to next sunrise).

SECTION: WHAT THIS TOOL COVERS
TARABALA counts from the birth nakshatra to the transit Moon's nakshatra (inclusive, 1-27) and folds it into nine taras: Janma, Sampat, Vipat, Kshema, Pratyak, Sadhana, Naidhana, Mitra, Ati-Mitra. The 27 counts make three rounds of nine, and the first tara of each round has its own name: Janma (count 1, Moon in the birth nakshatra), Anujanma (count 10) and Trijanma (count 19). The top-level tara is the one at sunrise; transit_nakshatras lists every nakshatra the Moon passes through that day with its tara. CHANDRABALA is the transit Moon's house from the natal Moon (favourable in 1, 3, 6, 7, 10, 11). Also returns the transit nakshatra's quality type with suitable and unsuitable activities, and a daily score out of 4.

SECTION: WORKFLOW
BEFORE: None — birth data computes everything needed.
AFTER: asterwise_get_panchanga — the day's full panchanga; asterwise_get_muhurta — Tarabala-aware windows for an activity.

SECTION: INPUT CONTRACT
birth: BirthData (date, time, lat, lon, timezone). Unknown birth time: omit time; never pass '00:00'. target_date (optional, YYYY-MM-DD): defaults to today at the birth place.

SECTION: OUTPUT CONTRACT
data.target_date, data.birth_nakshatra {name, index}, data.natal_moon_sign_index.
data.transit_moon {nakshatra, nakshatra_index, rashi_index} at sunrise.
data.tarabala {tara_number, count_from_birth, cycle, cycle_name, name, meaning, is_favorable, is_moon_in_birth_nakshatra, interpretation}.
data.transit_nakshatras[] {nakshatra, nakshatra_index, start, end, tara{...}}.
data.chandrabala {moon_house_from_natal, is_favorable, favorable_houses}. data.daily_score {score, max_score, label}.
data.transit_nakshatra_quality {...}, data.nakshatra_activities {favorable[], unfavorable[]}.

SECTION: COMPUTE CLASS
MEDIUM_COMPUTE

SECTION: ERROR CONTRACT
INVALID_PARAMS (local): BirthData violations. INTERNAL_ERROR: upstream failure.

SECTION: DO NOT CONFUSE WITH
asterwise_get_nakshatra_details — static nakshatra reference, not a personal prediction.
asterwise_get_panchanga — daily panchanga (tithi, yoga, karana), not Tarabala."""

DIVISIONAL_CHART = """Computes divisional (varga) charts from BirthData; pass chart_type for one varga, or omit chart_type for all sixteen. Each planet in each varga comes with its dignity there and whether it is vargottama; with a known birth time, each chart also has its own lagna, every planet's whole-sign house from that lagna, and a houses table.

SECTION: WHAT THIS TOOL COVERS
Charts: D1, D2, D3, D4, D7, D9, D10, D12, D16, D20, D24, D27, D30, D40, D45, D60. D30 uses the BPHS odd/even Trimshamsa table and places every body, Sun and Moon included; D60 counts from the planet's own sign (Jagannatha Hora defaults). dignity (exalted, debilitated, own_sign, friendly, neutral, enemy) is given for the seven classical planets; is_vargottama means the same sign as in D1. Does not return Shadbala (asterwise_get_chart_strength) or graha drishti (asterwise_get_natal_chart).

SECTION: WORKFLOW
BEFORE: RECOMMENDED — asterwise_get_natal_chart — anchor D1 before reading higher vargas.
AFTER: None.

SECTION: INPUT CONTRACT
chart_type enum is enforced locally. BirthData follows the global contract. Unknown birth time: omit time; lagna, houses and the houses table are then left out (birth_time_provided=false).

SECTION: OUTPUT CONTRACT
data.<chart> (e.g. data.D9): planet_name → {sign, sign_num (0-11), degree, dignity, is_vargottama, house}; ascendant → {sign, sign_num, degree, is_vargottama} when the birth time is known.
data.houses (birth time known): {chart: [{house, sign, sign_num, lord, planets[]}]}.
data.birth_time_provided (bool).

SECTION: COMPUTE CLASS
MEDIUM_COMPUTE

SECTION: ERROR CONTRACT
INVALID_PARAMS (local): invalid chart_type. INTERNAL_ERROR: upstream failure.

SECTION: DO NOT CONFUSE WITH
asterwise_get_natal_chart — radix chart with houses and drishti, not the varga set.
asterwise_get_chart_strength — varga-based strength scores, not placements."""

GEOCODE = """Turns a place name into latitude, longitude and IANA timezone for the other tools, which all take lat, lon and timezone.

SECTION: WHAT THIS TOOL COVERS
Searches OpenStreetMap (Nominatim) place names and returns up to `limit` matches, each with a label, city, state, country, latitude, longitude and timezone. Repeat matches for one place (same city, state and country within 25 km) are listed once. When several places share a name, ambiguous is true: pick one, or narrow with a comma ('Fatehabad, Haryana') or country ('in', 'us').

SECTION: WORKFLOW
BEFORE: None.
AFTER: any tool that takes lat, lon and timezone — asterwise_get_natal_chart, asterwise_get_panchanga, asterwise_get_muhurta, asterwise_get_festival_calendar and others.

SECTION: INPUT CONTRACT
query: place name, at least 2 characters (required). limit: 1-10 (default 5). country: optional ISO 3166 alpha-2 code.

SECTION: OUTPUT CONTRACT
data.query, data.count, data.ambiguous, data.tip (when ambiguous), data.results[]: label, city, state, country, latitude, longitude, timezone, place_id.

SECTION: ERROR CONTRACT
INTERNAL_ERROR: no match (city_not_found) or upstream failure.

SECTION: DO NOT CONFUSE WITH
None — this is the only place-lookup tool."""
