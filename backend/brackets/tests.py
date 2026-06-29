from datetime import timedelta
from unittest import mock

from django.core import signing
from django.test import RequestFactory, TestCase
from django.core.management import call_command
from django.utils import timezone

from brackets.models import Bracket, Invite, InviteSubmission, Match, Pick, Team, site_settings
from brackets.middleware import DevCorsMiddleware
from brackets.services import espn
from brackets.services.scoring import score_bracket
from brackets.services.fallback import fallback_slots


class BracketTests(TestCase):
    def test_fallback_schedule_uses_real_match_numbers_and_links(self):
        slots = {slot["match_number"]: slot for slot in fallback_slots()}

        self.assertEqual(slots[73]["team_one"]["abbreviation"], "RSA")
        self.assertEqual(slots[73]["team_two"]["abbreviation"], "CAN")
        self.assertEqual(slots[97]["previous_slot_one"], "r16-02")
        self.assertEqual(slots[97]["previous_slot_two"], "r16-01")
        self.assertEqual(slots[104]["previous_slot_one"], "sf-01")
        self.assertEqual(slots[104]["previous_slot_two"], "sf-02")
        self.assertEqual(slots[73]["venue_name"], "SoFi Stadium")
        self.assertEqual(slots[73]["venue_city"], "Inglewood, CA")

    def test_espn_sync_fetches_each_knockout_date(self):
        with mock.patch("brackets.services.espn.fetch_scoreboard", return_value=None) as fetch:
            payloads = espn.fetch_scoreboards()

        self.assertEqual(payloads, [])
        self.assertIn(mock.call("20260628"), fetch.mock_calls)
        self.assertIn(mock.call("20260719"), fetch.mock_calls)
        self.assertGreater(fetch.call_count, 1)

    def test_espn_parser_ignores_unmapped_placeholder_events(self):
        payload = {
            "events": [
                {
                    "id": "placeholder",
                    "name": "Round of 32 15 Winner vs Round of 32 16 Winner",
                    "shortName": "Round of 32",
                    "date": "2026-06-28T19:00Z",
                    "competitions": [
                        {
                            "venue": {
                                "fullName": "SoFi Stadium",
                                "address": {"city": "Inglewood", "state": "California"},
                            },
                            "competitors": [
                                {
                                    "team": {
                                        "abbreviation": "RD32",
                                        "displayName": "Round of 32 15 Winner",
                                    }
                                },
                                {
                                    "team": {
                                        "abbreviation": "RD32",
                                        "displayName": "Round of 32 16 Winner",
                                    }
                                },
                            ],
                            "status": {"type": {"description": "Scheduled", "completed": False}},
                        }
                    ],
                }
            ]
        }

        parsed = espn.parse_scoreboard(payload)

        self.assertEqual(parsed, [])

    def test_espn_parser_maps_official_match_number(self):
        payload = {
            "events": [
                {
                    "id": "73",
                    "name": "South Africa vs Canada - Match 73",
                    "shortName": "Match 73",
                    "date": "2026-06-28T19:00Z",
                    "competitions": [
                        {
                            "venue": {
                                "fullName": "SoFi Stadium",
                                "address": {"city": "Inglewood", "state": "CA"},
                            },
                            "competitors": [
                                {
                                    "score": "0",
                                    "team": {"abbreviation": "RSA", "displayName": "South Africa"},
                                },
                                {
                                    "score": "1",
                                    "winner": True,
                                    "team": {"abbreviation": "CAN", "displayName": "Canada"},
                                },
                            ],
                            "status": {"type": {"description": "Final", "completed": True}},
                        }
                    ],
                }
            ]
        }

        parsed = espn.parse_scoreboard(payload)

        self.assertEqual(parsed[0]["slot_key"], "r32-01")
        self.assertEqual(parsed[0]["match_number"], 73)
        self.assertEqual(parsed[0]["winner"]["abbreviation"], "CAN")
        self.assertEqual(parsed[0]["venue_name"], "SoFi Stadium")
        self.assertEqual(parsed[0]["venue_city"], "Inglewood, CA")

    def test_espn_parser_uses_live_display_clock_for_active_matches(self):
        payload = {
            "events": [
                {
                    "id": "76",
                    "name": "Brazil vs Japan - Match 76",
                    "shortName": "Match 76",
                    "date": "2026-06-29T17:00Z",
                    "competitions": [
                        {
                            "venue": {
                                "fullName": "NRG Stadium",
                                "address": {"city": "Houston", "state": "TX"},
                            },
                            "competitors": [
                                {
                                    "score": "2",
                                    "team": {"abbreviation": "BRA", "displayName": "Brazil"},
                                },
                                {
                                    "score": "1",
                                    "team": {"abbreviation": "JPN", "displayName": "Japan"},
                                },
                            ],
                            "status": {
                                "displayClock": "67'",
                                "type": {"description": "In Progress", "completed": False},
                            },
                        }
                    ],
                }
            ]
        }

        parsed = espn.parse_scoreboard(payload)

        self.assertEqual(parsed[0]["slot_key"], "r32-05")
        self.assertEqual(parsed[0]["status"], "67'")
        self.assertEqual(parsed[0]["score_one"], 2)
        self.assertEqual(parsed[0]["score_two"], 1)

    def test_espn_parser_converts_live_seconds_clock_to_match_minute(self):
        payload = {
            "events": [
                {
                    "id": "74",
                    "name": "Germany vs Paraguay - Match 74",
                    "shortName": "Match 74",
                    "date": "2026-06-29T20:30Z",
                    "competitions": [
                        {
                            "competitors": [
                                {
                                    "score": "0",
                                    "team": {"abbreviation": "GER", "displayName": "Germany"},
                                },
                                {
                                    "score": "1",
                                    "team": {"abbreviation": "PAR", "displayName": "Paraguay"},
                                },
                            ],
                            "status": {
                                "clock": 2700,
                                "type": {"description": "In Progress", "completed": False},
                            },
                        }
                    ],
                }
            ]
        }

        parsed = espn.parse_scoreboard(payload)

        self.assertEqual(parsed[0]["slot_key"], "r32-03")
        self.assertEqual(parsed[0]["status"], "45'")
        self.assertEqual(parsed[0]["score_one"], 0)
        self.assertEqual(parsed[0]["score_two"], 1)

    def test_espn_parser_converts_live_mmss_clock_to_match_minute(self):
        payload = {
            "events": [
                {
                    "id": "74",
                    "name": "Germany vs Paraguay - Match 74",
                    "shortName": "Match 74",
                    "date": "2026-06-29T20:30Z",
                    "competitions": [
                        {
                            "competitors": [
                                {
                                    "score": "0",
                                    "team": {"abbreviation": "GER", "displayName": "Germany"},
                                },
                                {
                                    "score": "1",
                                    "team": {"abbreviation": "PAR", "displayName": "Paraguay"},
                                },
                            ],
                            "status": {
                                "displayClock": "45:00",
                                "type": {"description": "In Progress", "completed": False},
                            },
                        }
                    ],
                }
            ]
        }

        parsed = espn.parse_scoreboard(payload)

        self.assertEqual(parsed[0]["status"], "45'")

    def test_espn_parser_ignores_pregame_zero_clock_and_scores(self):
        payload = {
            "events": [
                {
                    "id": "75",
                    "name": "Netherlands vs Morocco - Match 75",
                    "shortName": "Match 75",
                    "date": "2026-06-30T01:00Z",
                    "competitions": [
                        {
                            "venue": {
                                "fullName": "Estadio BBVA",
                                "address": {"city": "Guadalupe", "state": "NL"},
                            },
                            "competitors": [
                                {
                                    "score": "0",
                                    "team": {"abbreviation": "NED", "displayName": "Netherlands"},
                                },
                                {
                                    "score": "0",
                                    "team": {"abbreviation": "MAR", "displayName": "Morocco"},
                                },
                            ],
                            "status": {
                                "displayClock": "0'",
                                "type": {"description": "Scheduled", "completed": False},
                            },
                        }
                    ],
                }
            ]
        }

        parsed = espn.parse_scoreboard(payload)

        self.assertEqual(parsed[0]["slot_key"], "r32-02")
        self.assertEqual(parsed[0]["status"], "Scheduled")
        self.assertIsNone(parsed[0]["score_one"])
        self.assertIsNone(parsed[0]["score_two"])

    def test_espn_merge_keeps_canonical_fallback_venue_format(self):
        merged = espn._merge_with_fallback(
            [
                {
                    "slot_key": "r32-01",
                    "match_number": 73,
                    "round_key": "r32",
                    "round_name": "Round of 32",
                    "points": 25,
                    "position": 1,
                    "team_one": {"espn_id": "RSA", "abbreviation": "RSA", "display_name": "South Africa"},
                    "team_two": {"espn_id": "CAN", "abbreviation": "CAN", "display_name": "Canada"},
                    "winner": {"espn_id": "CAN", "abbreviation": "CAN", "display_name": "Canada"},
                    "is_complete": True,
                    "venue_name": "SoFi Stadium",
                    "venue_city": "Inglewood, California, USA",
                }
            ]
        )
        slot = {item["slot_key"]: item for item in merged}["r32-01"]

        self.assertEqual(slot["venue_name"], "SoFi Stadium")
        self.assertEqual(slot["venue_city"], "Inglewood, CA")
        self.assertTrue(slot["is_complete"])

    def test_slug_collision_uses_title(self):
        first = Bracket.objects.create(title="Jared's Bracket")
        second = Bracket.objects.create(title="Jared's Bracket")

        self.assertEqual(first.slug, "jareds-bracket")
        self.assertEqual(second.slug, "jareds-bracket-2")

    def test_scores_completed_correct_picks(self):
        usa = Team.objects.create(
            espn_id="usa", abbreviation="USA", display_name="United States"
        )
        france = Team.objects.create(
            espn_id="fra", abbreviation="FRA", display_name="France"
        )
        Match.objects.create(
            slot_key="final",
            round_key="final",
            round_name="Final",
            points=400,
            position=1,
            is_complete=True,
            team_one=usa,
            team_two=france,
            winner=usa,
        )
        bracket = Bracket.objects.create(title="Winner")
        Pick.objects.create(
            bracket=bracket,
            slot_key="final",
            team_espn_id="usa",
            team_abbreviation="USA",
            team_display_name="United States",
        )

        score = score_bracket(bracket)

        self.assertEqual(score["total"], 400)
        self.assertEqual(score["max_points"], 2000)

    def test_scores_incorrect_picks_as_zero(self):
        usa = Team.objects.create(
            espn_id="usa", abbreviation="USA", display_name="United States"
        )
        france = Team.objects.create(
            espn_id="fra", abbreviation="FRA", display_name="France"
        )
        Match.objects.create(
            slot_key="final",
            round_key="final",
            round_name="Final",
            points=400,
            position=1,
            is_complete=True,
            team_one=usa,
            team_two=france,
            winner=usa,
        )
        bracket = Bracket.objects.create(title="Runner Up")
        Pick.objects.create(
            bracket=bracket,
            slot_key="final",
            team_espn_id="fra",
            team_abbreviation="FRA",
            team_display_name="France",
        )

        score = score_bracket(bracket)

        self.assertEqual(score["total"], 0)
        self.assertFalse(score["picks"][0]["correct"])

    def test_score_rounds_follow_bracket_order(self):
        usa = Team.objects.create(
            espn_id="usa", abbreviation="USA", display_name="United States"
        )
        france = Team.objects.create(
            espn_id="fra", abbreviation="FRA", display_name="France"
        )
        Match.objects.create(
            slot_key="final",
            round_key="final",
            round_name="Final",
            points=400,
            position=1,
            team_one=usa,
            team_two=france,
        )
        Match.objects.create(
            slot_key="r32-01",
            round_key="r32",
            round_name="Round of 32",
            points=25,
            position=1,
            team_one=usa,
            team_two=france,
        )
        bracket = Bracket.objects.create(title="Round Order")
        Pick.objects.create(
            bracket=bracket,
            slot_key="final",
            team_espn_id="usa",
            team_abbreviation="USA",
            team_display_name="United States",
        )
        Pick.objects.create(
            bracket=bracket,
            slot_key="r32-01",
            team_espn_id="usa",
            team_abbreviation="USA",
            team_display_name="United States",
        )

        score = score_bracket(bracket)

        self.assertEqual(
            [round_summary["round_key"] for round_summary in score["rounds"]],
            ["r32", "final"],
        )

    def test_invite_submission_is_one_per_device(self):
        invite = Invite.objects.create(name="Office Pool")
        bracket = Bracket.objects.create(title="Locked", is_locked=True)
        InviteSubmission.objects.create(invite=invite, bracket=bracket, device_key="device-1")

        duplicate = InviteSubmission(invite=invite, bracket=bracket, device_key="device-1")

        with self.assertRaises(Exception):
            duplicate.validate_constraints()

    def test_locked_bracket_has_edit_token(self):
        bracket = Bracket.objects.create(title="Locked", is_locked=True)

        self.assertTrue(bracket.edit_token)

    def test_delete_requires_developer_mode(self):
        bracket = Bracket.objects.create(title="Delete Me")

        response = self.client.delete(f"/api/brackets/{bracket.slug}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Bracket.objects.filter(id=bracket.id).exists())

    def test_created_brackets_are_locked_by_default(self):
        response = self.client.post(
            "/api/brackets/",
            data={"title": "Public Form", "picks": []},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        bracket = Bracket.objects.get(title="Public Form")
        self.assertTrue(bracket.is_locked)
        self.assertFalse(response.json()["can_edit"])

    def test_delete_with_developer_token(self):
        bracket = Bracket.objects.create(title="Locked Delete", is_locked=True)
        developer_token = signing.TimestampSigner(
            salt="world-cup-bracket-dev-mode"
        ).sign("developer")

        allowed = self.client.delete(
            f"/api/brackets/{bracket.slug}/",
            data={"developer_token": developer_token},
            content_type="application/json",
        )

        self.assertEqual(allowed.status_code, 200)
        self.assertFalse(Bracket.objects.filter(id=bracket.id).exists())

    def test_developer_mode_endpoint_uses_terminal_password(self):
        with mock.patch.dict("os.environ", {"BRACKET_DEV_PASSWORD": "secret"}):
            blocked = self.client.post(
                "/api/developer-mode/",
                data={"password": "wrong"},
                content_type="application/json",
            )
            allowed = self.client.post(
                "/api/developer-mode/",
                data={"password": "secret"},
                content_type="application/json",
            )

        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
        self.assertIn("developer_token", allowed.json())

    def test_developer_token_can_edit_locked_bracket(self):
        bracket = Bracket.objects.create(title="Locked Editable", is_locked=True)
        developer_token = signing.TimestampSigner(
            salt="world-cup-bracket-dev-mode"
        ).sign("developer")

        blocked = self.client.put(
            f"/api/brackets/{bracket.slug}/",
            data={"title": "Blocked"},
            content_type="application/json",
        )
        allowed = self.client.put(
            f"/api/brackets/{bracket.slug}/",
            data={"title": "Allowed", "developer_token": developer_token},
            content_type="application/json",
        )

        bracket.refresh_from_db()
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(bracket.title, "Allowed")

    def test_developer_token_can_create_personalized_invite(self):
        developer_token = signing.TimestampSigner(
            salt="world-cup-bracket-dev-mode"
        ).sign("developer")

        response = self.client.post(
            "/api/invites/",
            data={"bracket_title": "Adrienne", "developer_token": developer_token},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["bracket_title"], "Adrienne")

    def test_personalized_invite_uses_invite_title(self):
        invite = Invite.objects.create(name="Adrienne", bracket_title="Adrienne")

        response = self.client.post(
            f"/api/invites/{invite.token}/",
            data={
                "device_key": "device-1",
                "title": "Wrong",
                "picks": [],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["title"], "Adrienne")

    def test_locked_submissions_block_invite_submit(self):
        invite = Invite.objects.create(name="Adrienne", bracket_title="Adrienne")
        settings = site_settings()
        settings.submissions_locked = True
        settings.save()

        response = self.client.post(
            f"/api/invites/{invite.token}/",
            data={"device_key": "device-1", "picks": []},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("Submissions are locked", response.json()["error"])

    def test_developer_can_toggle_submission_lock_and_list_invites(self):
        Invite.objects.create(name="Adrienne", bracket_title="Adrienne")
        developer_token = signing.TimestampSigner(
            salt="world-cup-bracket-dev-mode"
        ).sign("developer")

        lock_response = self.client.put(
            "/api/submissions-lock/",
            data={"submissions_locked": True, "developer_token": developer_token},
            content_type="application/json",
        )
        invites_response = self.client.get(
            "/api/invites/",
            HTTP_X_DEVELOPER_TOKEN=developer_token,
        )

        self.assertEqual(lock_response.status_code, 200)
        self.assertTrue(lock_response.json()["submissions_locked"])
        self.assertEqual(invites_response.status_code, 200)
        self.assertTrue(invites_response.json()["submissions_locked"])
        self.assertEqual(invites_response.json()["invites"][0]["bracket_title"], "Adrienne")

    def test_export_requires_developer_mode(self):
        bracket = Bracket.objects.create(title="Export Me", is_locked=True)
        Pick.objects.create(
            bracket=bracket,
            slot_key="final",
            team_espn_id="can",
            team_abbreviation="CAN",
            team_display_name="Canada",
        )
        developer_token = signing.TimestampSigner(
            salt="world-cup-bracket-dev-mode"
        ).sign("developer")

        blocked = self.client.get("/api/data/export/")
        allowed = self.client.get("/api/data/export/", HTTP_X_DEVELOPER_TOKEN=developer_token)

        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.json()["brackets"][0]["title"], "Export Me")
        self.assertEqual(allowed.json()["brackets"][0]["picks"][0]["team"]["abbreviation"], "CAN")

    def test_import_restores_brackets_invites_and_settings(self):
        developer_token = signing.TimestampSigner(
            salt="world-cup-bracket-dev-mode"
        ).sign("developer")
        payload = {
            "version": 1,
            "developer_token": developer_token,
            "brackets": [
                {
                    "title": "Imported",
                    "slug": "imported",
                    "is_locked": True,
                    "edit_token": "saved-edit-token",
                    "picks": [
                        {
                            "slot_key": "final",
                            "team": {
                                "espn_id": "can",
                                "abbreviation": "CAN",
                                "display_name": "Canada",
                                "logo_url": "https://example.com/canada.png",
                            },
                        }
                    ],
                }
            ],
            "invites": [
                {
                    "name": "Imported Invite",
                    "bracket_title": "Imported",
                    "token": "invite-token",
                    "is_active": True,
                }
            ],
            "invite_submissions": [
                {
                    "invite_token": "invite-token",
                    "bracket_slug": "imported",
                    "device_key": "device-1",
                    "ip_address": "127.0.0.1",
                }
            ],
            "site_settings": {"submissions_locked": True},
        }

        response = self.client.post(
            "/api/data/import/",
            data=payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"]["brackets"], 1)
        bracket = Bracket.objects.get(slug="imported")
        self.assertEqual(bracket.title, "Imported")
        self.assertTrue(bracket.is_locked)
        self.assertEqual(bracket.edit_token, "saved-edit-token")
        self.assertEqual(bracket.picks.get(slot_key="final").team_display_name, "Canada")
        self.assertTrue(InviteSubmission.objects.filter(bracket=bracket).exists())
        self.assertTrue(site_settings().submissions_locked)

    def test_delete_bracket_command_deletes_locked_bracket(self):
        bracket = Bracket.objects.create(title="Command Delete", is_locked=True)

        call_command("delete_bracket", bracket.slug, "--yes")

        self.assertFalse(Bracket.objects.filter(id=bracket.id).exists())

    def test_api_exceptions_are_json(self):
        request = RequestFactory().get("/api/matches/")
        middleware = DevCorsMiddleware(lambda _request: None)

        response = middleware.process_exception(request, RuntimeError("boom"))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("RuntimeError: boom", response.content.decode())

    def test_health_endpoint_is_lightweight(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_leaderboard_includes_spotlight_live_match_and_user_picks(self):
        canada = Team.objects.create(espn_id="CAN", abbreviation="CAN", display_name="Canada")
        netherlands = Team.objects.create(
            espn_id="NED", abbreviation="NED", display_name="Netherlands"
        )
        Match.objects.create(
            slot_key="r16-01",
            match_number=90,
            round_key="r16",
            round_name="Round of 16",
            points=50,
            position=1,
            status="67'",
            team_one=canada,
            team_two=netherlands,
            score_one=1,
            score_two=0,
        )
        picked = Bracket.objects.create(title="Picked")
        empty = Bracket.objects.create(title="Empty")
        Pick.objects.create(
            bracket=picked,
            slot_key="r16-01",
            team_espn_id="CAN",
            team_abbreviation="CAN",
            team_display_name="Canada",
        )

        response = self.client.get("/api/leaderboard/")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["spotlight_match"]["slot_key"], "r16-01")
        self.assertEqual(payload["spotlight_state"], "live")
        self.assertEqual(payload["live_match"]["slot_key"], "r16-01")
        by_title = {bracket["title"]: bracket for bracket in payload["brackets"]}
        self.assertEqual(by_title["Picked"]["spotlight_pick"]["team"]["display_name"], "Canada")
        self.assertIsNone(by_title["Empty"].get("spotlight_pick"))

    def test_leaderboard_includes_next_match_between_live_games(self):
        brazil = Team.objects.create(espn_id="BRA", abbreviation="BRA", display_name="Brazil")
        japan = Team.objects.create(espn_id="JPN", abbreviation="JPN", display_name="Japan")
        Match.objects.create(
            slot_key="rd32-04",
            match_number=76,
            round_key="rd32",
            round_name="Round of 32",
            points=25,
            position=4,
            status="Scheduled",
            starts_at=timezone.now() + timedelta(hours=2),
            team_one=brazil,
            team_two=japan,
        )
        picked = Bracket.objects.create(title="Picked")
        Pick.objects.create(
            bracket=picked,
            slot_key="rd32-04",
            team_espn_id="BRA",
            team_abbreviation="BRA",
            team_display_name="Brazil",
        )

        response = self.client.get("/api/leaderboard/")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["spotlight_match"]["slot_key"], "rd32-04")
        self.assertEqual(payload["spotlight_state"], "upcoming")
        self.assertIsNone(payload["live_match"])
        self.assertEqual(payload["brackets"][0]["spotlight_pick"]["team"]["display_name"], "Brazil")
