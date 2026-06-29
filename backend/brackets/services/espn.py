import json
import re
from urllib.error import URLError
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


def sync_matches():
    payload = fetch_scoreboard()
    parsed_slots = parse_scoreboard(payload) if payload else []
    if parsed_slots:
        upsert_slots(_merge_with_fallback(parsed_slots))
        return {"source": "espn", "matches": len(parsed_slots)}

    fallback = fallback_slots()
    upsert_slots(fallback)
    return {"source": "fallback", "matches": len(fallback)}


def fetch_scoreboard():
    try:
        with urlopen(ESPN_SCOREBOARD_URL, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, json.JSONDecodeError):
        return None


def parse_scoreboard(payload):
    events = payload.get("events", [])
    parsed = []
    round_positions = {}

    fallback_by_slot = {slot["slot_key"]: slot for slot in fallback_slots()}
    round_positions = {
        round_key: 0
        for round_key in ["r32", "r16", "qf", "sf", "final"]
    }

    for event in events:
        competition = (event.get("competitions") or [{}])[0]
        competitors = competition.get("competitors", [])
        if len(competitors) < 2:
            continue

        round_key, round_name, points, expected_count = _round_from_event(event, competition)
        if not round_key:
            continue

        fallback_slot = _fallback_slot_for_competitors(
            fallback_by_slot.values(), round_key, competitors
        )
        if fallback_slot:
            slot_key = fallback_slot["slot_key"]
            position = fallback_slot["position"]
        else:
            round_positions[round_key] = round_positions.get(round_key, 0) + 1
            position = round_positions[round_key]
        if position > expected_count:
            continue

        slot_key = fallback_slot["slot_key"] if fallback_slot else (
            "final" if round_key == "final" else f"{round_key}-{position:02d}"
        )
        team_one = _team_from_competitor(competitors[0])
        team_two = _team_from_competitor(competitors[1])
        winner = None
        for competitor in competitors:
            if competitor.get("winner") is True:
                winner = _team_from_competitor(competitor)

        status = competition.get("status", {}).get("type", {})
        parsed.append(
            {
                "slot_key": slot_key,
                "match_number": fallback_slot.get("match_number") if fallback_slot else None,
                "round_key": round_key,
                "round_name": round_name,
                "points": points,
                "position": position,
                "previous_slot_one": fallback_slot.get("previous_slot_one", "")
                if fallback_slot
                else "",
                "previous_slot_two": fallback_slot.get("previous_slot_two", "")
                if fallback_slot
                else "",
                "team_one": team_one,
                "team_two": team_two,
                "status": status.get("description") or status.get("name") or "",
                "is_complete": status.get("completed") is True,
                "winner": winner,
                "score_one": _score(competitors[0]),
                "score_two": _score(competitors[1]),
                "source": "espn",
                "source_event_id": str(event.get("id", "")),
                "starts_at": parse_datetime(event.get("date", "")) if event.get("date") else None,
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
        by_slot[parsed_slot["slot_key"]] = {**fallback_slot, **parsed_slot}
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
