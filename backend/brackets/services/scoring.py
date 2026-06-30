from brackets.models import Match


MAX_POINTS = 2000
ROUND_ORDER = ["r32", "r16", "qf", "sf", "final"]


def score_bracket(bracket):
    matches = {match.slot_key: match for match in Match.objects.all()}
    reachability_cache = {}
    round_totals = {}
    total = 0
    possible_remaining = 0
    scored_picks = []

    for pick in bracket.picks.all():
        match = matches.get(pick.slot_key)
        if not match:
            continue

        round_summary = round_totals.setdefault(
            match.round_key,
            {
                "round_key": match.round_key,
                "round_name": match.round_name,
                "earned": 0,
                "possible": 0,
            },
        )
        round_summary["possible"] += match.points

        correct = None
        points = 0
        if match.is_complete and match.winner:
            correct = pick.team_espn_id == match.winner.espn_id
            if correct:
                points = match.points
                total += points
                round_summary["earned"] += points
        elif _team_can_reach_slot(pick.team_espn_id, match.slot_key, matches, reachability_cache):
            possible_remaining += match.points

        scored_picks.append(
            {
                "slot_key": pick.slot_key,
                "team": pick.as_team(),
                "points": points,
                "correct": correct,
                "match_complete": match.is_complete,
                "match_winner": _team_payload(match.winner) if match.winner else None,
                "possible": correct is True
                or (
                    correct is None
                    and _team_can_reach_slot(
                        pick.team_espn_id, match.slot_key, matches, reachability_cache
                    )
                ),
            }
        )

    return {
        "total": total,
        "max_points": MAX_POINTS,
        "possible_remaining": possible_remaining,
        "max_possible": total + possible_remaining,
        "rounds": [
            round_totals[round_key]
            for round_key in ROUND_ORDER
            if round_key in round_totals
        ],
        "picks": scored_picks,
    }


def _team_payload(team):
    return {
        "espn_id": team.espn_id,
        "abbreviation": team.abbreviation,
        "display_name": team.display_name,
        "logo_url": team.logo_url,
    }


def _team_can_reach_slot(team_id, slot_key, matches, cache):
    cache_key = (team_id, slot_key)
    if cache_key in cache:
        return cache[cache_key]

    match = matches.get(slot_key)
    if not match:
        cache[cache_key] = False
        return False

    if match.is_complete:
        result = bool(match.winner and match.winner.espn_id == team_id)
        cache[cache_key] = result
        return result

    if not match.previous_slot_one and not match.previous_slot_two:
        result = team_id in {
            match.team_one.espn_id if match.team_one else None,
            match.team_two.espn_id if match.team_two else None,
        }
        cache[cache_key] = result
        return result

    result = any(
        _team_can_reach_slot(team_id, previous_slot, matches, cache)
        for previous_slot in (match.previous_slot_one, match.previous_slot_two)
        if previous_slot
    )
    cache[cache_key] = result
    return result
