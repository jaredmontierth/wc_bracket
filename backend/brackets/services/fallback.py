from django.utils.dateparse import parse_datetime

ROUND_CONFIG = [
    ("r32", "Round of 32", 25, 16),
    ("r16", "Round of 16", 50, 8),
    ("qf", "Quarterfinals", 100, 4),
    ("sf", "Semifinals", 200, 2),
    ("final", "Final", 400, 1),
]

TEAMS = {
    "RSA": "South Africa",
    "CAN": "Canada",
    "BRA": "Brazil",
    "JPN": "Japan",
    "GER": "Germany",
    "PAR": "Paraguay",
    "NED": "Netherlands",
    "MAR": "Morocco",
    "CIV": "Ivory Coast",
    "NOR": "Norway",
    "FRA": "France",
    "SWE": "Sweden",
    "MEX": "Mexico",
    "ECU": "Ecuador",
    "ENG": "England",
    "COD": "DR Congo",
    "BEL": "Belgium",
    "SEN": "Senegal",
    "USA": "United States",
    "BIH": "Bosnia and Herzegovina",
    "ESP": "Spain",
    "AUT": "Austria",
    "POR": "Portugal",
    "CRO": "Croatia",
    "SUI": "Switzerland",
    "ALG": "Algeria",
    "AUS": "Australia",
    "EGY": "Egypt",
    "ARG": "Argentina",
    "CPV": "Cape Verde",
    "COL": "Colombia",
    "GHA": "Ghana",
}

MATCHES = [
    # Stored in bracket-advancement order. Match numbers preserve the official schedule.
    ("r32-01", 73, "r32", 1, "2026-06-28T19:00:00Z", "RSA", "CAN", "", ""),
    ("r32-02", 75, "r32", 2, "2026-06-29T20:30:00Z", "NED", "MAR", "", ""),
    ("r32-03", 74, "r32", 3, "2026-06-29T20:30:00Z", "GER", "PAR", "", ""),
    ("r32-04", 77, "r32", 4, "2026-06-30T21:00:00Z", "FRA", "SWE", "", ""),
    ("r32-05", 76, "r32", 5, "2026-06-29T17:00:00Z", "BRA", "JPN", "", ""),
    ("r32-06", 78, "r32", 6, "2026-06-30T17:00:00Z", "CIV", "NOR", "", ""),
    ("r32-07", 79, "r32", 7, "2026-07-01T01:00:00Z", "MEX", "ECU", "", ""),
    ("r32-08", 80, "r32", 8, "2026-07-01T16:00:00Z", "ENG", "COD", "", ""),
    ("r32-09", 83, "r32", 9, "2026-07-02T23:00:00Z", "POR", "CRO", "", ""),
    ("r32-10", 84, "r32", 10, "2026-07-02T19:00:00Z", "ESP", "AUT", "", ""),
    ("r32-11", 81, "r32", 11, "2026-07-02T00:00:00Z", "USA", "BIH", "", ""),
    ("r32-12", 82, "r32", 12, "2026-07-01T20:00:00Z", "BEL", "SEN", "", ""),
    ("r32-13", 86, "r32", 13, "2026-07-03T22:00:00Z", "ARG", "CPV", "", ""),
    ("r32-14", 88, "r32", 14, "2026-07-03T18:00:00Z", "AUS", "EGY", "", ""),
    ("r32-15", 85, "r32", 15, "2026-07-03T03:00:00Z", "SUI", "ALG", "", ""),
    ("r32-16", 87, "r32", 16, "2026-07-04T01:30:00Z", "COL", "GHA", "", ""),
    ("r16-01", 90, "r16", 1, "2026-07-04T17:00:00Z", None, None, "r32-01", "r32-02"),
    ("r16-02", 89, "r16", 2, "2026-07-04T21:00:00Z", None, None, "r32-03", "r32-04"),
    ("r16-03", 91, "r16", 3, "2026-07-05T20:00:00Z", None, None, "r32-05", "r32-06"),
    ("r16-04", 92, "r16", 4, "2026-07-06T00:00:00Z", None, None, "r32-07", "r32-08"),
    ("r16-05", 93, "r16", 5, "2026-07-06T19:00:00Z", None, None, "r32-09", "r32-10"),
    ("r16-06", 94, "r16", 6, "2026-07-07T00:00:00Z", None, None, "r32-11", "r32-12"),
    ("r16-07", 95, "r16", 7, "2026-07-07T16:00:00Z", None, None, "r32-13", "r32-14"),
    ("r16-08", 96, "r16", 8, "2026-07-07T20:00:00Z", None, None, "r32-15", "r32-16"),
    ("qf-01", 97, "qf", 1, "2026-07-09T20:00:00Z", None, None, "r16-02", "r16-01"),
    ("qf-02", 98, "qf", 2, "2026-07-10T19:00:00Z", None, None, "r16-05", "r16-06"),
    ("qf-03", 99, "qf", 3, "2026-07-11T21:00:00Z", None, None, "r16-03", "r16-04"),
    ("qf-04", 100, "qf", 4, "2026-07-12T01:00:00Z", None, None, "r16-07", "r16-08"),
    ("sf-01", 101, "sf", 1, "2026-07-14T19:00:00Z", None, None, "qf-01", "qf-02"),
    ("sf-02", 102, "sf", 2, "2026-07-15T19:00:00Z", None, None, "qf-03", "qf-04"),
    ("final", 104, "final", 1, "2026-07-19T19:00:00Z", None, None, "sf-01", "sf-02"),
]


def fallback_slots():
    round_config = {round_key: (round_name, points) for round_key, round_name, points, _ in ROUND_CONFIG}
    slots = []
    for slot_key, match_number, round_key, position, starts_at, team_one, team_two, prev_one, prev_two in MATCHES:
        round_name, points = round_config[round_key]
        slots.append(
            {
                "slot_key": slot_key,
                "match_number": match_number,
                "round_key": round_key,
                "round_name": round_name,
                "points": points,
                "position": position,
                "previous_slot_one": prev_one,
                "previous_slot_two": prev_two,
                "team_one": _team(team_one),
                "team_two": _team(team_two),
                "status": "scheduled",
                "is_complete": False,
                "winner": None,
                "score_one": None,
                "score_two": None,
                "source": "fallback",
                "starts_at": parse_datetime(starts_at),
            }
        )
    return slots


def _team(abbreviation):
    if not abbreviation:
        return None
    return {
        "espn_id": abbreviation,
        "abbreviation": abbreviation,
        "display_name": TEAMS[abbreviation],
        "logo_url": f"https://a.espncdn.com/i/teamlogos/countries/500/{abbreviation.lower()}.png",
    }
