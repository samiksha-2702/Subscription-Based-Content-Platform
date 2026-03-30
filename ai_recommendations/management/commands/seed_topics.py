from django.core.management.base import BaseCommand
from ai_recommendations.models import Topic

TOPICS = [
    ("Python Basics", "python-basics", "python", "beginner"),
    ("Python Control Flow", "python-control-flow", "python", "beginner"),
    ("Python OOP", "python-oop", "python", "intermediate"),
    ("Python Libraries", "python-libraries", "python", "intermediate"),
    ("Python Practice", "python-practice", "python", "intermediate"),

    ("Java Basics", "java-basics", "java", "beginner"),
    ("Java OOP", "java-oop", "java", "intermediate"),

    ("C++ Basics", "cpp-basics", "cpp", "beginner"),

    ("JS Basics", "js-basics", "javascript", "beginner"),
    ("JS Async", "js-async", "javascript", "intermediate"),  # ✅ ADDED

    ("SQL Basics", "sql-basics", "sql", "beginner"),
    ("SQL Joins", "sql-joins", "sql", "intermediate"),       # ✅ ADDED

    ("DSA Basics", "dsa-basics", "dsa", "beginner"),
    ("DSA Linear", "dsa-linear", "dsa", "beginner"),         # ✅ ADDED
]

PREREQS = [
    ("python-oop", "python-basics"),
    ("python-libraries", "python-oop"),
    ("java-oop", "java-basics"),
    ("js-async", "js-basics"),
    ("sql-joins", "sql-basics"),
    ("dsa-linear", "dsa-basics"),
]


class Command(BaseCommand):
    help = "Seed Topic data with AI-ready structure"

    def handle(self, *args, **kwargs):

        created = 0
        updated = 0

        # ────────────────
        # STEP 1: Topics
        # ────────────────
        for name, slug, module, difficulty in TOPICS:

            obj, was_created = Topic.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "module": module,
                    "difficulty": difficulty,
                    "keywords": [name.lower(), module],
                    "resource_url": f"/learn/{slug}/"
                }
            )

            if was_created:
                created += 1
            else:
                # ✅ Update existing topics (important)
                obj.name = name
                obj.module = module
                obj.difficulty = difficulty
                obj.keywords = [name.lower(), module]
                obj.resource_url = f"/learn/{slug}/"
                obj.save()

                updated += 1

        # ────────────────
        # STEP 2: Prerequisites
        # ────────────────
        for topic_slug, prereq_slug in PREREQS:

            try:
                topic = Topic.objects.get(slug=topic_slug)
                prereq = Topic.objects.get(slug=prereq_slug)

                if not topic.prerequisites.filter(id=prereq.id).exists():
                    topic.prerequisites.add(prereq)

            except Topic.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Missing: {topic_slug} or {prereq_slug}")
                )

        # ────────────────
        # FINAL OUTPUT
        # ────────────────
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created: {created} | Updated: {updated} | Total: {len(TOPICS)}"
            )
        )