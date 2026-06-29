from brackets.models import Bracket, Match, Pick
from brackets.services.scoring import score_bracket


def team_payload(team):
    if not team:
        return None
    return {
        "espn_id": team.espn_id,
        "abbreviation": team.abbreviation,
        "display_name": team.display_name,
        "logo_url": team.logo_url,
    }


def match_payload(match):
    return {
        "slot_key": match.slot_key,
        "match_number": match.match_number,
        "round_key": match.round_key,
        "round_name": match.round_name,
        "points": match.points,
        "position": match.position,
        "previous_slot_one": match.previous_slot_one,
        "previous_slot_two": match.previous_slot_two,
        "starts_at": match.starts_at.isoformat() if match.starts_at else None,
        "status": match.status,
        "is_complete": match.is_complete,
        "source": match.source,
        "team_one": team_payload(match.team_one),
        "team_two": team_payload(match.team_two),
        "score_one": match.score_one,
        "score_two": match.score_two,
        "winner": team_payload(match.winner),
    }


def tournament_payload():
    matches = [match_payload(match) for match in Match.objects.all()]
    return {
        "matches": matches,
        "rounds": [
            {"round_key": "r32", "round_name": "Round of 32", "points": 25},
            {"round_key": "r16", "round_name": "Round of 16", "points": 50},
            {"round_key": "qf", "round_name": "Quarterfinals", "points": 100},
            {"round_key": "sf", "round_name": "Semifinals", "points": 200},
            {"round_key": "final", "round_name": "Final", "points": 400},
        ],
    }


def bracket_list_payload(bracket):
    score = score_bracket(bracket)
    champion_pick = bracket.picks.filter(slot_key="final").first()
    return {
        "id": bracket.id,
        "title": bracket.title,
        "slug": bracket.slug,
        "created_at": bracket.created_at.isoformat(),
        "is_locked": bracket.is_locked,
        "champion_pick": pick_payload(champion_pick) if champion_pick else None,
        "score": score,
    }


def bracket_detail_payload(bracket, can_edit=None):
    payload = bracket_list_payload(bracket)
    payload["is_locked"] = bracket.is_locked
    payload["can_edit"] = (not bracket.is_locked) if can_edit is None else can_edit
    payload["picks"] = [pick_payload(pick) for pick in bracket.picks.all()]
    return payload


def pick_payload(pick):
    return {
        "slot_key": pick.slot_key,
        "team": pick.as_team(),
    }


def upsert_picks(bracket, picks):
    keep_slots = []
    for item in picks:
        team = item.get("team") or {}
        slot_key = item.get("slot_key")
        team_id = team.get("espn_id")
        display_name = team.get("display_name")
        if not slot_key or not team_id or not display_name:
            continue
        keep_slots.append(slot_key)
        Pick.objects.update_or_create(
            bracket=bracket,
            slot_key=slot_key,
            defaults={
                "team_espn_id": team_id,
                "team_abbreviation": team.get("abbreviation", ""),
                "team_display_name": display_name,
                "team_logo_url": team.get("logo_url", ""),
            },
        )
    if keep_slots:
        bracket.picks.exclude(slot_key__in=keep_slots).delete()
