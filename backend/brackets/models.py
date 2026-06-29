from django.db import models
from django.utils.text import slugify
import secrets


class Team(models.Model):
    espn_id = models.CharField(max_length=80, unique=True)
    abbreviation = models.CharField(max_length=20, blank=True)
    display_name = models.CharField(max_length=120)
    logo_url = models.URLField(blank=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self):
        return self.display_name


class Match(models.Model):
    slot_key = models.CharField(max_length=40, unique=True)
    source_event_id = models.CharField(max_length=80, blank=True, db_index=True)
    match_number = models.PositiveIntegerField(null=True, blank=True, unique=True)
    round_key = models.CharField(max_length=20)
    round_name = models.CharField(max_length=60)
    points = models.PositiveIntegerField()
    position = models.PositiveIntegerField()
    previous_slot_one = models.CharField(max_length=40, blank=True)
    previous_slot_two = models.CharField(max_length=40, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=40, blank=True)
    is_complete = models.BooleanField(default=False)
    source = models.CharField(max_length=20, default="fallback")
    team_one = models.ForeignKey(
        Team, null=True, blank=True, related_name="team_one_matches", on_delete=models.SET_NULL
    )
    team_two = models.ForeignKey(
        Team, null=True, blank=True, related_name="team_two_matches", on_delete=models.SET_NULL
    )
    score_one = models.IntegerField(null=True, blank=True)
    score_two = models.IntegerField(null=True, blank=True)
    winner = models.ForeignKey(
        Team, null=True, blank=True, related_name="won_matches", on_delete=models.SET_NULL
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return f"{self.round_name} {self.position}"


class Bracket(models.Model):
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    is_locked = models.BooleanField(default=False)
    edit_token = models.CharField(max_length=80, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug_from_title(self.title)
        if not self.edit_token:
            self.edit_token = secrets.token_urlsafe(24)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Pick(models.Model):
    bracket = models.ForeignKey(Bracket, related_name="picks", on_delete=models.CASCADE)
    slot_key = models.CharField(max_length=40)
    team_espn_id = models.CharField(max_length=80)
    team_abbreviation = models.CharField(max_length=20, blank=True)
    team_display_name = models.CharField(max_length=120)
    team_logo_url = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["bracket", "slot_key"], name="unique_pick_per_slot")
        ]
        ordering = ["slot_key"]

    def as_team(self):
        return {
            "espn_id": self.team_espn_id,
            "abbreviation": self.team_abbreviation,
            "display_name": self.team_display_name,
            "logo_url": self.team_logo_url,
        }


class Invite(models.Model):
    name = models.CharField(max_length=120)
    bracket_title = models.CharField(max_length=120, blank=True)
    token = models.SlugField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(18).replace("_", "-")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class InviteSubmission(models.Model):
    invite = models.ForeignKey(Invite, related_name="submissions", on_delete=models.CASCADE)
    bracket = models.OneToOneField(Bracket, related_name="invite_submission", on_delete=models.CASCADE)
    device_key = models.CharField(max_length=120)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["invite", "device_key"], name="unique_invite_submission_per_device"
            )
        ]
        ordering = ["-created_at"]


class SiteSettings(models.Model):
    submissions_locked = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "site settings"

    def __str__(self):
        return "Site settings"


def site_settings():
    settings, _ = SiteSettings.objects.get_or_create(pk=1)
    return settings


def unique_slug_from_title(title):
    base_slug = slugify(title)[:120] or "bracket"
    slug = base_slug
    suffix = 2
    while Bracket.objects.filter(slug=slug).exists():
        suffix_text = f"-{suffix}"
        slug = f"{base_slug[: 140 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return slug
