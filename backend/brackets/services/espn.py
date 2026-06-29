import json
import re
from collections import OrderedDict
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.utils.dateparse import parse_datetime

from brackets.models import Match, Team
from brackets.services.fallback import fallback_slots

ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
)

ROUND_ALIASES = {
    "round of 32": ("r32", "Round of 32", 25, 16),
    "round 32": ("r32", "Round of 32", 25, 16),
    "round of 16": ("r16", "Round of 16", 50, 8),
    "round 16": ("r16", "Round of 16", 50, 8),
    "eighth finals": ("r16", "Round of 16", 50, 8),
    "quarterfinal": ("qf", "Quarterfinals", 100, 4),
    "quarterfinals": ("qf", "Quarterfinals", 100, 4),
    "semifinal": ("sf", "Semifinals", 200, 2),
    "semifinals": ("sf", "Semifinals", 200, 2),
    "final": ("final", "Final", 400, 1),
}

ROUND_ORDER = {"r32": 1, "r16": 2, "qf": 3, "sf": 4, "final": 5}

REGION_ABBREVIATIONS = {
    "Alberta": "AB",
    "British Columbia": "BC",
    "California": "CA",
    "Ciudad de Mexico": "CDMX",
    "Ciudad de México": "CDMX",
    "Florida": "FL",
    "Georgia": "GA",
    "Massachusetts": "MA",
    "Mexico City": "CDMX",
    "Missouri": "MO",
    "New Jersey": "NJ",
    "Nuevo Leon": "NL",
    "Nuevo León": "NL",
    "Ontario": "ON",
    "Pennsylvania": "PA",
    "Quebec": "QC",
    "Québec": "QC",
    "Texas": "TX",
    "Washington": "WA",
}


def sync_matches():
    parsed_slots = []
    for payload in fetch_scoreboards():
        parsed_slots.extend(parse_scoreboard(payload))
    if parsed_slots:
        parsed_slots = _dedupe_slots(parsed_slots)
        upsert_slots(_merge_with_fallback(parsed_slots))
        return {"source": "espn", "matches": len(parsed_slots)}

    fallback = fallback_slots()
    upsert_slots(fallback)
    return {"source": "fallback", "matches": len(fallback)}


def fetch_scoreboards():
    payloads = []
    for date in _scoreboard_dates():
        payload = fetch_scoreboard(date)
        if payload:
            payloads.append(payload)
    return payloads


def fetch_scoreboard(date=None):
    url = ESPN_SCOREBOARD_URL
    if date:
        url = f"{url}?{urlencode({'dates': date})}"
    try:
        with urlopen(url, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError):
        return None


def parse_scoreboard(payload):
    events = payload.get("events", [])
    parsed = []

    fallback = fallback_slots()

    for event in events:
        competition = (event.get("competitions") or [{}])[0]
        competitors = competition.get("competitors", [])
        if len(competitors) < 2:
            continue

        round_key, round_name, points, expected_count = _round_from_event(event, competition)
        if not round_key:
            match_number = _match_number_from_event(event, competition)
            fallback_slot = _fallback_slot_for_match_number(fallback, match_number)
            if not fallback_slot:
                continue
            round_key = fallback_slot["round_key"]
            round_name = fallback_slot["round_name"]
            points = fallback_slot["points"]

        fallback_slot = _fallback_slot_for_event(fallback, round_key, event, competition, competitors)
        if not fallback_slot:
            continue

        team_one = _team_from_competitor(competitors[0])
        team_two = _team_from_competitor(competitors[1])
        winner = None
        for competitor in competitors:
            if competitor.get("winner") is True:
                winner = _team_from_competitor(competitor)

        status_payload = competition.get("status", {})
        status = status_payload.get("type", {})
        venue = _venue_from_competition(competition)
        parsed.append(
            {
                "slot_key": fallback_slot["slot_key"],
                "match_number": fallback_slot.get("match_number"),
                "round_key": round_key,
                "round_name": round_name,
                "points": points,
                "position": fallback_slot["position"],
                "previous_slot_one": fallback_slot.get("previous_slot_one", ""),
                "previous_slot_two": fallback_slot.get("previous_slot_two", ""),
                "team_one": team_one,
                "team_two": team_two,
                "status": _status_label(status_payload),
                "is_complete": status.get("completed") is True,
                "winner": winner,
                "score_one": _score(competitors[0]),
                "score_two": _score(competitors[1]),
                "source": "espn",
                "source_event_id": str(event.get("id", "")),
                "starts_at": parse_datetime(event.get("date", "")) if event.get("date") else None,
                "venue_name": venue["name"],
                "venue_city": venue["city"],
            }
        )

    parsed.sort(key=lambda item: (ROUND_ORDER[item["round_key"]], item["position"]))
    return parsed


def upsert_slots(slots):
    for slot in slots:
        team_one = _upsert_team(slot["team_one"])
        team_two = _upsert_team(slot["team_two"])
        winner = _upsert_team(slot["winner"])
        Match.objects.update_or_create(
            slot_key=slot["slot_key"],
            defaults={
                "source_event_id": slot.get("source_event_id", ""),
                "match_number": slot.get("match_number"),
                "round_key": slot["round_key"],
                "round_name": slot["round_name"],
                "points": slot["points"],
                "position": slot["position"],
                "previous_slot_one": slot.get("previous_slot_one", ""),
                "previous_slot_two": slot.get("previous_slot_two", ""),
                "starts_at": slot.get("starts_at"),
                "venue_name": slot.get("venue_name", ""),
                "venue_city": slot.get("venue_city", ""),
                "status": slot.get("status", ""),
                "is_complete": slot.get("is_complete", False),
                "source": slot.get("source", "fallback"),
                "team_one": team_one,
                "team_two": team_two,
                "winner": winner,
                "score_one": slot.get("score_one"),
                "score_two": slot.get("score_two"),
            },
        )


def ensure_matches_available():
    if not Match.objects.exists():
        sync_matches()


def _merge_with_fallback(parsed_slots):
    by_slot = {slot["slot_key"]: slot for slot in fallback_slots()}
    for parsed_slot in parsed_slots:
        fallback_slot = by_slot.get(parsed_slot["slot_key"], {})
        merged = {**fallback_slot, **parsed_slot}
        if fallback_slot.get("venue_name"):
            merged["venue_name"] = fallback_slot["venue_name"]
        if fallback_slot.get("venue_city"):
            merged["venue_city"] = fallback_slot["venue_city"]
        by_slot[parsed_slot["slot_key"]] = merged
    return list(by_slot.values())


def _scoreboard_dates():
    dates = OrderedDict()
    for slot in fallback_slots():
        starts_at = slot.get("starts_at")
        if starts_at:
            dates[starts_at.strftime("%Y%m%d")] = True
    return list(dates.keys())


def _status_label(status_payload):
    status_type = status_payload.get("type", {})
    if status_type.get("completed") is True:
        return status_type.get("description") or status_type.get("name") or ""

    display_clock = str(status_payload.get("displayClock") or "").strip()
    if display_clock and display_clock != "0:00":
        return display_clock

    clock = status_payload.get("clock")
    if isinstance(clock, (int, float)) and clock > 0:
        return f"{int(clock)}'"

    return status_type.get("description") or status_type.get("name") or ""


def _dedupe_slots(slots):
    by_slot = OrderedDict()
    for slot in slots:
        by_slot[slot["slot_key"]] = slot
    return list(by_slot.values())


def _round_from_event(event, competition):
    candidates = [
        event.get("season", {}).get("slug"),
        event.get("season", {}).get("type"),
        event.get("week", {}).get("text"),
        event.get("name"),
        event.get("shortName"),
        competition.get("notes", [{}])[0].get("headline")
        if competition.get("notes")
        else None,
    ]
    haystack = " ".join(str(candidate or "").lower() for candidate in candidates)
    haystack = re.sub(r"[^a-z0-9]+", " ", haystack)
    for alias, config in ROUND_ALIASES.items():
        if alias in haystack:
            return config
    return (None, None, None, None)


def _team_from_competitor(competitor):
    team = competitor.get("team", {})
    if not team:
        return None
    logos = team.get("logos") or []
    abbreviation = team.get("abbreviation", "")
    return {
        "espn_id": abbreviation or str(team.get("id") or team.get("displayName")),
        "abbreviation": abbreviation,
        "display_name": team.get("displayName") or team.get("name") or "TBD",
        "logo_url": logos[0].get("href", "") if logos else team.get("logo", ""),
    }


def _fallback_slot_for_event(slots, round_key, event, competition, competitors):
    match_number = _match_number_from_event(event, competition)
    if match_number is not None:
        slot = _fallback_slot_for_match_number(slots, match_number)
        if slot and slot["round_key"] == round_key:
            return slot
    return _fallback_slot_for_competitors(slots, round_key, competitors)


def _fallback_slot_for_match_number(slots, match_number):
    if match_number is None:
        return None
    for slot in slots:
        if slot.get("match_number") == match_number:
            return slot
    return None


def _fallback_slot_for_competitors(slots, round_key, competitors):
    abbreviations = {
        (competitor.get("team") or {}).get("abbreviation")
        for competitor in competitors
    }
    abbreviations.discard(None)
    if len(abbreviations) != 2:
        return None
    for slot in slots:
        if slot["round_key"] != round_key:
            continue
        team_abbreviations = {
            team["abbreviation"]
            for team in [slot.get("team_one"), slot.get("team_two")]
            if team
        }
        if team_abbreviations == abbreviations:
            return slot
    return None


def _match_number_from_event(event, competition):
    candidates = [
        event.get("name"),
        event.get("shortName"),
        event.get("description"),
        competition.get("notes", [{}])[0].get("headline")
        if competition.get("notes")
        else None,
    ]
    for candidate in candidates:
        match = re.search(r"\bmatch\s+(\d{2,3})\b", str(candidate or ""), re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _venue_from_competition(competition):
    venue = competition.get("venue") or {}
    address = venue.get("address") or {}
    city = address.get("city", "")
    region = _region_abbreviation(address.get("state") or address.get("country") or "")
    city_parts = [
        city,
        region,
    ]
    return {
        "name": venue.get("fullName") or venue.get("displayName") or "",
        "city": ", ".join(part for part in city_parts if part),
    }


def _region_abbreviation(value):
    if not value:
        return ""
    if value.upper() in {"USA", "US", "UNITED STATES", "CAN", "CANADA", "MEX", "MEXICO"}:
        return ""
    if len(value) <= 4 and value.upper() == value:
        return value
    return REGION_ABBREVIATIONS.get(value, value)


def _upsert_team(team_payload):
    if not team_payload:
        return None
    team, _ = Team.objects.update_or_create(
        espn_id=team_payload["espn_id"],
        defaults={
            "abbreviation": team_payload.get("abbreviation", ""),
            "display_name": team_payload.get("display_name", "TBD"),
            "logo_url": team_payload.get("logo_url", ""),
        },
    )
    return team


def _score(competitor):
    score = competitor.get("score")
    if score in (None, ""):
        return None
    try:
        return int(score)
    except ValueError:
        return None
