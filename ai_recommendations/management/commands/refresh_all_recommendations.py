# ai_recommendations/management/commands/refresh_all_recommendations.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ai_recommendations.ai_engine import RecommendationEngine  # adjust path if needed

class Command(BaseCommand):
    help = "Refresh AI recommendations for all active users."

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', type=str,
            help='Refresh only a specific user',
        )

    def handle(self, *args, **options):
        qs = User.objects.filter(is_active=True)
        if options['username']:
            qs = qs.filter(username=options['username'])

        total = qs.count()
        self.stdout.write(f"Refreshing recommendations for {total} user(s)...")

        errors = 0
        for user in qs:
            try:
                engine = RecommendationEngine(user)
                result = engine.run(save_to_db=True)
                self.stdout.write(
                    f"  ✅ {user.username}: "
                    f"{len(result['weaknesses'])} weak areas, "
                    f"{len(result['recommendations'])} recommendations"
                )
            except Exception as e:
                errors += 1
                self.stderr.write(f"  ❌ {user.username}: {e}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {total - errors}/{total} users refreshed successfully."
            )
        )