from django.core.management.base import BaseCommand, CommandError

from brackets.models import Bracket


class Command(BaseCommand):
    help = "Delete a bracket by slug or exact title, including locked invite brackets."

    def add_arguments(self, parser):
        parser.add_argument("identifier", help="Bracket slug or exact title")
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Actually delete the bracket. Without this flag the command previews the match.",
        )

    def handle(self, *args, **options):
        identifier = options["identifier"]
        bracket = (
            Bracket.objects.filter(slug=identifier).first()
            or Bracket.objects.filter(title=identifier).first()
        )
        if not bracket:
            raise CommandError(f"No bracket found for {identifier!r}.")

        self.stdout.write(f"Found: {bracket.title} ({bracket.slug})")
        self.stdout.write(f"Locked: {'yes' if bracket.is_locked else 'no'}")
        if not options["yes"]:
            self.stdout.write("Preview only. Re-run with --yes to delete it.")
            return

        bracket.delete()
        self.stdout.write(self.style.SUCCESS("Deleted."))
