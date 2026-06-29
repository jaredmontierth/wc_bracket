import json
import os
import re
import secrets
import threading

from django.core import signing
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from brackets.models import Bracket, Invite, InviteSubmission, Match, Pick, site_settings
from brackets.serializers import (
    bracket_detail_payload,
    bracket_list_payload,
    match_payload,
    pick_payload,
    tournament_payload,
    upsert_picks,
)
from brackets.services.espn import ensure_matches_available, sync_matches

SYNC_LOCK = threading.Lock()
DEV_TOKEN_SALT = "world-cup-bracket-dev-mode"
DEV_TOKEN_MAX_AGE = 60 * 60 * 12


def health_view(request):
    return JsonResponse({"ok": True})


def options_ok(request):
    if request.method == "OPTIONS":
        return JsonResponse({})
    return None


@csrf_exempt
def matches_view(request):
    if response := options_ok(request):
        return response
    ensure_matches_available()
    if request.GET.get("refresh") == "1":
        if SYNC_LOCK.acquire(blocking=False):
            try:
                sync_matches()
            finally:
                SYNC_LOCK.release()
    return JsonResponse(tournament_payload())


@csrf_exempt
def sync_view(request):
    if response := options_ok(request):
        return response
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    result = sync_matches()
    return JsonResponse(result)


@csrf_exempt
def brackets_view(request):
    if response := options_ok(request):
        return response
    ensure_matches_available()
    if request.method == "GET":
        brackets = [bracket_list_payload(bracket) for bracket in Bracket.objects.all()]
        brackets.sort(key=lambda item: item["score"]["total"], reverse=True)
        return JsonResponse({"brackets": brackets})
    if request.method == "POST":
        body = _json_body(request)
        title = (body.get("title") or "").strip()
        if not title:
            return JsonResponse({"error": "A bracket title is required."}, status=400)
        bracket = Bracket.objects.create(title=title, is_locked=True)
        upsert_picks(bracket, body.get("picks", []))
        return JsonResponse(bracket_detail_payload(bracket), status=201)
    return JsonResponse({"error": "Unsupported method"}, status=405)


@csrf_exempt
def bracket_detail_view(request, slug):
    if response := options_ok(request):
        return response
    ensure_matches_available()
    bracket = _get_bracket(slug)
    if not bracket:
        return JsonResponse({"error": "Bracket not found"}, status=404)
    if request.method == "GET":
        can_edit = _has_developer_access(request) or _has_edit_access(request, bracket)
        return JsonResponse(bracket_detail_payload(bracket, can_edit=can_edit))
    if request.method == "PUT":
        body = _json_body(request)
        if not (_has_developer_access(request, body) or _has_edit_access(request, bracket, body)):
            return JsonResponse({"error": "This bracket is locked."}, status=403)
        title = (body.get("title") or bracket.title).strip()
        if title:
            bracket.title = title
            bracket.save(update_fields=["title", "updated_at"])
        upsert_picks(bracket, body.get("picks", []))
        return JsonResponse(bracket_detail_payload(bracket, can_edit=True))
    if request.method == "DELETE":
        body = _json_body(request)
        if not _has_developer_access(request, body):
            return JsonResponse({"error": "Developer mode is required to delete brackets."}, status=403)
        bracket.delete()
        return JsonResponse({"deleted": True})
    return JsonResponse({"error": "Unsupported method"}, status=405)


def leaderboard_view(request):
    ensure_matches_available()
    spotlight_match, spotlight_state = _spotlight_match()
    brackets = [bracket_list_payload(bracket) for bracket in Bracket.objects.all()]
    if spotlight_match:
        for bracket_payload in brackets:
            bracket_payload["spotlight_pick"] = _spotlight_pick_payload(
                bracket_payload["id"], spotlight_match
            )
    brackets.sort(key=lambda item: item["score"]["total"], reverse=True)
    spotlight_payload = match_payload(spotlight_match) if spotlight_match else None
    return JsonResponse(
        {
            "brackets": brackets,
            "spotlight_match": spotlight_payload,
            "spotlight_state": spotlight_state,
            "live_match": spotlight_payload if spotlight_state == "live" else None,
            "submissions_locked": site_settings().submissions_locked,
        }
    )


def _spotlight_match():
    matches = Match.objects.filter(is_complete=False).order_by("starts_at", "position")
    for match in matches:
        if _is_live_match(match):
            return match, "live"
    now = timezone.now()
    for match in matches:
        if match.starts_at and match.starts_at >= now:
            return match, "upcoming"
    return None, ""


def _is_live_match(match):
    status = (match.status or "").lower()
    return bool(re.search(r"live|progress|half|extra|^[1-9]\d*'?$", status))


def _spotlight_pick_payload(bracket_id, spotlight_match):
    pick = Pick.objects.filter(bracket_id=bracket_id, slot_key=spotlight_match.slot_key).first()
    return pick_payload(pick) if pick else None


@csrf_exempt
def developer_mode_view(request):
    if response := options_ok(request):
        return response
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    password = os.environ.get("BRACKET_DEV_PASSWORD", "")
    if not password:
        return JsonResponse({"error": "Developer password is not configured."}, status=403)
    body = _json_body(request)
    submitted = body.get("password") or ""
    if not secrets.compare_digest(submitted, password):
        return JsonResponse({"error": "Incorrect developer password."}, status=403)
    token = signing.TimestampSigner(salt=DEV_TOKEN_SALT).sign("developer")
    return JsonResponse({"developer_token": token})


@csrf_exempt
def invites_view(request):
    if response := options_ok(request):
        return response
    if request.method == "GET":
        if not _has_developer_access(request):
            return JsonResponse({"error": "Developer mode is required to list invites."}, status=403)
        return JsonResponse(
            {
                "submissions_locked": site_settings().submissions_locked,
                "invites": [_invite_payload(invite) for invite in Invite.objects.all()],
            }
        )
    if request.method != "POST":
        return JsonResponse({"error": "Unsupported method"}, status=405)
    body = _json_body(request)
    if not _has_developer_access(request, body):
        return JsonResponse({"error": "Developer mode is required to create invites."}, status=403)
    bracket_title = (body.get("bracket_title") or body.get("name") or "").strip()
    if not bracket_title:
        return JsonResponse({"error": "A bracket name is required."}, status=400)
    invite = Invite.objects.create(name=bracket_title, bracket_title=bracket_title)
    return JsonResponse(
        {
            "name": invite.name,
            "bracket_title": invite.bracket_title,
            "token": invite.token,
        },
        status=201,
    )


@csrf_exempt
def submissions_lock_view(request):
    if response := options_ok(request):
        return response
    if request.method != "PUT":
        return JsonResponse({"error": "PUT required"}, status=405)
    body = _json_body(request)
    if not _has_developer_access(request, body):
        return JsonResponse({"error": "Developer mode is required to lock submissions."}, status=403)
    settings = site_settings()
    settings.submissions_locked = bool(body.get("submissions_locked"))
    settings.save(update_fields=["submissions_locked", "updated_at"])
    return JsonResponse({"submissions_locked": settings.submissions_locked})


@csrf_exempt
def data_export_view(request):
    if response := options_ok(request):
        return response
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)
    if not _has_developer_access(request):
        return JsonResponse({"error": "Developer mode is required to export data."}, status=403)
    return JsonResponse(export_data_payload())


@csrf_exempt
def data_import_view(request):
    if response := options_ok(request):
        return response
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    body = _json_body(request)
    if not _has_developer_access(request, body):
        return JsonResponse({"error": "Developer mode is required to import data."}, status=403)
    try:
        summary = import_data_payload(body)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse({"imported": True, "summary": summary})


@csrf_exempt
def invite_view(request, token):
    if response := options_ok(request):
        return response
    ensure_matches_available()
    invite = _get_invite(token)
    if not invite or not invite.is_active:
        return JsonResponse({"error": "Invite not found"}, status=404)
    settings = site_settings()

    if request.method == "GET":
        device_key = (request.GET.get("device_key") or "").strip()
        submission = _submission_for_device(invite, device_key)
        return JsonResponse(
            {
                "name": invite.name,
                "bracket_title": invite.bracket_title or invite.name,
                "token": invite.token,
                "submissions_locked": settings.submissions_locked,
                "submitted": submission is not None,
                "bracket": bracket_detail_payload(submission.bracket, can_edit=False)
                if submission
                else None,
            }
        )

    if request.method == "POST":
        if settings.submissions_locked:
            return JsonResponse({"error": "Submissions are locked."}, status=403)
        body = _json_body(request)
        device_key = (body.get("device_key") or "").strip()
        if not device_key:
            return JsonResponse({"error": "Device key is required."}, status=400)
        existing_submission = _submission_for_device(invite, device_key)
        if existing_submission:
            return JsonResponse(
                {
                    "error": "This device has already submitted a bracket for this invite.",
                    "bracket": bracket_detail_payload(existing_submission.bracket, can_edit=False),
                },
                status=409,
            )

        title = (invite.bracket_title or body.get("title") or "").strip()
        if not title:
            return JsonResponse({"error": "A bracket title is required."}, status=400)
        bracket = Bracket.objects.create(title=title, is_locked=True)
        upsert_picks(bracket, body.get("picks", []))
        InviteSubmission.objects.create(
            invite=invite,
            bracket=bracket,
            device_key=device_key,
            ip_address=_client_ip(request),
        )
        return JsonResponse(bracket_detail_payload(bracket, can_edit=False), status=201)

    return JsonResponse({"error": "Unsupported method"}, status=405)


def _json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def _get_bracket(slug):
    try:
        return Bracket.objects.get(slug=slug)
    except Bracket.DoesNotExist:
        return None


def _get_invite(token):
    try:
        return Invite.objects.get(token=token)
    except Invite.DoesNotExist:
        return None


def _submission_for_device(invite, device_key):
    if not device_key:
        return None
    try:
        return InviteSubmission.objects.select_related("bracket").get(
            invite=invite, device_key=device_key
        )
    except InviteSubmission.DoesNotExist:
        return None


def _invite_payload(invite):
    submission = invite.submissions.select_related("bracket").first()
    return {
        "name": invite.name,
        "bracket_title": invite.bracket_title or invite.name,
        "token": invite.token,
        "is_active": invite.is_active,
        "created_at": invite.created_at.isoformat(),
        "submitted": submission is not None,
        "submitted_at": submission.created_at.isoformat() if submission else None,
        "bracket": bracket_list_payload(submission.bracket) if submission else None,
    }


def export_data_payload():
    return {
        "version": 1,
        "brackets": [
            {
                "title": bracket.title,
                "slug": bracket.slug,
                "is_locked": bracket.is_locked,
                "edit_token": bracket.edit_token,
                "picks": [
                    {
                        "slot_key": pick.slot_key,
                        "team": pick.as_team(),
                    }
                    for pick in bracket.picks.all()
                ],
            }
            for bracket in Bracket.objects.prefetch_related("picks").all()
        ],
        "invites": [
            {
                "name": invite.name,
                "bracket_title": invite.bracket_title,
                "token": invite.token,
                "is_active": invite.is_active,
            }
            for invite in Invite.objects.all()
        ],
        "invite_submissions": [
            {
                "invite_token": submission.invite.token,
                "bracket_slug": submission.bracket.slug,
                "device_key": submission.device_key,
                "ip_address": submission.ip_address,
            }
            for submission in InviteSubmission.objects.select_related("invite", "bracket").all()
        ],
        "site_settings": {
            "submissions_locked": site_settings().submissions_locked,
        },
    }


@transaction.atomic
def import_data_payload(payload):
    if payload.get("version") != 1:
        raise ValueError("Unsupported import file.")

    brackets = payload.get("brackets")
    invites = payload.get("invites", [])
    submissions = payload.get("invite_submissions", [])
    settings_payload = payload.get("site_settings", {})

    if not isinstance(brackets, list):
        raise ValueError("Import file is missing brackets.")

    summary = {
        "brackets": 0,
        "picks": 0,
        "invites": 0,
        "invite_submissions": 0,
    }

    for item in brackets:
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        slug = (item.get("slug") or "").strip()
        if not title or not slug:
            continue
        edit_token = (item.get("edit_token") or "").strip()
        if edit_token and Bracket.objects.exclude(slug=slug).filter(edit_token=edit_token).exists():
            edit_token = ""
        bracket, _ = Bracket.objects.update_or_create(
            slug=slug,
            defaults={
                "title": title,
                "is_locked": bool(item.get("is_locked", True)),
                **({"edit_token": edit_token} if edit_token else {}),
            },
        )
        if not bracket.edit_token:
            bracket.save()
        Pick.objects.filter(bracket=bracket).delete()
        upsert_picks(bracket, item.get("picks", []))
        summary["brackets"] += 1
        summary["picks"] += bracket.picks.count()

    for item in invites:
        if not isinstance(item, dict):
            continue
        token = (item.get("token") or "").strip()
        name = (item.get("name") or item.get("bracket_title") or "").strip()
        if not token or not name:
            continue
        Invite.objects.update_or_create(
            token=token,
            defaults={
                "name": name,
                "bracket_title": (item.get("bracket_title") or name).strip(),
                "is_active": bool(item.get("is_active", True)),
            },
        )
        summary["invites"] += 1

    for item in submissions:
        if not isinstance(item, dict):
            continue
        invite_token = (item.get("invite_token") or "").strip()
        bracket_slug = (item.get("bracket_slug") or "").strip()
        device_key = (item.get("device_key") or "").strip()
        if not invite_token or not bracket_slug or not device_key:
            continue
        try:
            invite = Invite.objects.get(token=invite_token)
            bracket = Bracket.objects.get(slug=bracket_slug)
        except (Invite.DoesNotExist, Bracket.DoesNotExist):
            continue
        submission, created = InviteSubmission.objects.get_or_create(
            invite=invite,
            device_key=device_key,
            defaults={
                "bracket": bracket,
                "ip_address": item.get("ip_address") or None,
            },
        )
        if not created and submission.bracket_id != bracket.id:
            submission.bracket = bracket
            submission.ip_address = item.get("ip_address") or submission.ip_address
            submission.save(update_fields=["bracket", "ip_address"])
        summary["invite_submissions"] += 1

    settings = site_settings()
    settings.submissions_locked = bool(settings_payload.get("submissions_locked", settings.submissions_locked))
    settings.save(update_fields=["submissions_locked", "updated_at"])

    return summary


def _has_edit_access(request, bracket, body=None):
    if not bracket.is_locked:
        return True
    token = (
        request.headers.get("X-Bracket-Edit-Token")
        or request.GET.get("edit_token")
        or (body or {}).get("edit_token")
        or ""
    )
    return token and token == bracket.edit_token


def _has_developer_access(request, body=None):
    token = (
        request.headers.get("X-Developer-Token")
        or (body or {}).get("developer_token")
        or ""
    )
    if not token:
        return False
    try:
        value = signing.TimestampSigner(salt=DEV_TOKEN_SALT).unsign(
            token, max_age=DEV_TOKEN_MAX_AGE
        )
    except signing.BadSignature:
        return False
    return value == "developer"


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
