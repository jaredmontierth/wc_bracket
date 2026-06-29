from brackets.models import Match


MAX_POINTS = 2000
ROUND_ORDER = ["r32", "r16", "qf", "sf", "final"]


def score_bracket(bracket):
    matches = {match.slot_key: match for match in Match.objects.all()}
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
        elif not match.is_complete:
            possible_remaining += match.points

        scored_picks.append(
            {
                "slot_key": pick.slot_key,
                "team": pick.as_team(),
                "points": points,
                "correct": correct,
                "match_complete": match.is_complete,
                "match_winner": _team_payload(match.winner) if match.winner else None,
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
