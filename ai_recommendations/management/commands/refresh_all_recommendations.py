from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ai_recommendations.ai_engine import RecommendationEngine


class Command(BaseCommand):
    help = "Refresh AI recommendations for all active users."

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Refresh only a specific user',
        )

    def handle(self, *args, **options):

        qs = User.objects.filter(is_active=True)

        if options.get('username'):
            qs = qs.filter(username=options['username'])

        total = qs.count()
        self.stdout.write(self.style.WARNING(
            f"Refreshing recommendations for {total} user(s)..."
        ))

        success = 0
        errors = 0

        for user in qs.iterator():  # 🚀 memory efficient
            try:
                engine = RecommendationEngine(user)

                result = engine.run(save_to_db=True) or {}

                weaknesses = result.get('weaknesses', [])
                recommendations = result.get('recommendations', [])

                self.stdout.write(
                    f"  ✅ {user.username}: "
                    f"{len(weaknesses)} weak areas, "
                    f"{len(recommendations)} recommendations"
                )

                success += 1

            except Exception as e:
                errors += 1
                self.stderr.write(
                    f"  ❌ {user.username}: {str(e)}"
                )

        self.stdout.write("\n" + "="*50)
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {success}/{total} users refreshed successfully."
            )
        )

        if errors:
            self.stdout.write(
                self.style.ERROR(f"{errors} user(s) failed.")
            )