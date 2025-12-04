from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from pathlib import Path

class Command(BaseCommand):
    help = "Seed quiz data (E/M/H 1문항씩)"

    def handle(self, *args, **opts):
        fixture = Path(__file__).resolve().parents[2] / "fixtures" / "quizzes_seed.json"
        if not fixture.exists():
            raise CommandError(f"fixture not found: {fixture}")
        call_command("loaddata", str(fixture))
        self.stdout.write(self.style.SUCCESS("Quizzes seeded."))
