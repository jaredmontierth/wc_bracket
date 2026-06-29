from django.core.management.base import BaseCommand

from brackets.services.espn import sync_matches


class Command(BaseCommand):
    help = "Sync World Cup knockout results from ESPN, falling back to seeded slots."

    def handle(self, *args, **options):
        result = sync_matches()
        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {result['matches']} matches from {result['source']}."
            )
        )

