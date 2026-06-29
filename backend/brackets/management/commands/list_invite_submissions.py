from django.core.management.base import BaseCommand

from brackets.models import InviteSubmission


class Command(BaseCommand):
    help = "List locked invite submissions with private admin edit links."

    def add_arguments(self, parser):
        parser.add_argument("--host", default="http://127.0.0.1:5173")

    def handle(self, *args, **options):
        host = options["host"].rstrip("/")
        submissions = InviteSubmission.objects.select_related("invite", "bracket").all()
        if not submissions:
            self.stdout.write("No invite submissions yet.")
            return
        for submission in submissions:
            bracket = submission.bracket
            self.stdout.write(f"{bracket.title} ({submission.invite.name})")
            self.stdout.write(f"  view: {host}/brackets/{bracket.slug}")
            self.stdout.write(f"  edit: {host}/brackets/{bracket.slug}?edit={bracket.edit_token}")
