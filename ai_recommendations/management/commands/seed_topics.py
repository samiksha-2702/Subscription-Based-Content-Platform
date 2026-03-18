# ai_recommendations/management/commands/seed_topics.py
from django.core.management.base import BaseCommand
from ai_recommendations.models import Topic  # adjust if your Topic model is elsewhere

TOPICS = [
    ("Python Basics", "python-basics", "python", "beginner"),
    ("Python Control Flow", "python-control-flow", "python", "beginner"),
    ("Python OOP", "python-oop", "python", "intermediate"),
    ("Python Libraries", "python-libraries", "python", "intermediate"),
    ("Python Practice", "python-practice", "python", "intermediate"),
    ("Java Basics", "java-basics", "java", "beginner"),
    ("Java Control Flow", "java-control-flow", "java", "beginner"),
    ("Java OOP", "java-oop", "java", "intermediate"),
    ("Java Libraries", "java-libraries", "java", "intermediate"),
    ("C++ Basics", "cpp-basics", "cpp", "beginner"),
    ("C++ Control Flow", "cpp-control-flow", "cpp", "beginner"),
    ("C++ OOP", "cpp-oop", "cpp", "intermediate"),
    ("JS Basics", "js-basics", "javascript", "beginner"),
    ("JS Control Flow", "js-control-flow", "javascript", "beginner"),
    ("JS Async & ES6+", "js-async", "javascript", "intermediate"),
    ("SQL Basics", "sql-basics", "sql", "beginner"),
    ("SQL Queries", "sql-queries", "sql", "beginner"),
    ("SQL Joins", "sql-joins", "sql", "intermediate"),
    ("Advanced SQL", "sql-advanced", "sql", "advanced"),
    ("DSA Basics", "dsa-basics", "dsa", "beginner"),
    ("Linear Data Structures", "dsa-linear", "dsa", "beginner"),
    ("Sorting Algorithms", "dsa-sorting", "dsa", "intermediate"),
    ("DSA Practice", "dsa-practice", "dsa", "intermediate"),
    ("Interview Skills", "comm-interview", "communication", "beginner"),
    ("Verbal Communication", "comm-verbal", "communication", "beginner"),
    ("Listening Skills", "comm-listening", "communication", "beginner"),
    ("Time Management", "soft-time-mgmt", "soft_skills", "beginner"),
    ("Teamwork", "soft-teamwork", "soft_skills", "beginner"),
    ("Personality Development", "soft-personality", "soft_skills", "intermediate"),
]

PREREQS = [
    ("python-oop", "python-basics"),
    ("python-oop", "python-control-flow"),
    ("python-libraries", "python-oop"),
    ("python-practice", "python-basics"),
    ("java-oop", "java-basics"),
    ("java-libraries", "java-oop"),
    ("cpp-oop", "cpp-basics"),
    ("js-async", "js-basics"),
    ("sql-joins", "sql-queries"),
    ("sql-advanced", "sql-joins"),
    ("dsa-linear", "dsa-basics"),
    ("dsa-sorting", "dsa-linear"),
    ("dsa-practice", "dsa-basics"),
]

class Command(BaseCommand):
    help = "Seed the Topic table with PrepEdge topics and prerequisites."

    def handle(self, *args, **kwargs):
        created = 0
        for name, slug, module, difficulty in TOPICS:
            _, was_created = Topic.objects.get_or_create(
                slug=slug,
                defaults=dict(name=name, module=module, difficulty=difficulty)
            )
            if was_created:
                created += 1

        for topic_slug, prereq_slug in PREREQS:
            try:
                topic = Topic.objects.get(slug=topic_slug)
                prereq = Topic.objects.get(slug=prereq_slug)
                topic.prerequisites.add(prereq)
            except Topic.DoesNotExist:
                pass

        self.stdout.write(
            self.style.SUCCESS(f"✅ Seeded {created} new topics ({len(TOPICS)} total).")
        )