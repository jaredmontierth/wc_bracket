from django.core.management.base import BaseCommand

from brackets.models import Invite


class Command(BaseCommand):
    help = "Create a shareable bracket invite link."

    def add_arguments(self, parser):
        parser.add_argument("name", nargs="?", default="World Cup Bracket Invite")
        parser.add_argument("--host", default="http://127.0.0.1:5173")

    def handle(self, *args, **options):
        invite = Invite.objects.create(name=options["name"], bracket_title=options["name"])
        self.stdout.write(self.style.SUCCESS(f"Invite: {invite.name}"))
        self.stdout.write(f"{options['host'].rstrip('/')}/invite/{invite.token}")
