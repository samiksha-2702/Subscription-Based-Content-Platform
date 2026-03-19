"""
management/commands/setup_prepedge.py
======================================

One-shot setup command that:
  1. Seeds LiveSession table
  2. Creates admin user (from environment variables)
  3. Creates demo student user (safe defaults)

Run:
    python manage.py setup_prepedge
"""

import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed initial PrepEdge data (live sessions, demo users, subscriptions)'

    def handle(self, *args, **kwargs):
        self._seed_live_sessions()
        self._create_admin()
        self._create_demo_student()

        self.stdout.write(self.style.SUCCESS(
            '\n✅ PrepEdge setup complete!\n'
            '   ✔ Admin user created (check env variables)\n'
            '   ✔ Demo student ready\n'
            '   🌐 Visit → http://127.0.0.1:8000/\n'
        ))

    # ── 1. Live Sessions ─────────────────────────────────────────
    def _seed_live_sessions(self):
        from app1.models import LiveSession

        sessions = [
            ('Cloud Computing Essentials',
             'Learn AWS, Azure, and GCP fundamentals for interviews.',
             timezone.now() + timedelta(days=10)),

            ('Data Science Interview Tips',
             'Real interview questions from top data science roles.',
             timezone.now() + timedelta(days=20)),

            ('System Design for Beginners',
             'How to ace system design rounds.',
             timezone.now() + timedelta(days=35)),

            ('Python Advanced Concepts',
             'Decorators, generators, async Python.',
             timezone.now() + timedelta(days=50)),
        ]

        created = 0
        for title, desc, date in sessions:
            _, was_created = LiveSession.objects.get_or_create(
                title=title,
                defaults={'description': desc, 'session_date': date},
            )
            if was_created:
                created += 1

        self.stdout.write(f'  Live Sessions: {created} created')

    # ── 2. Admin user (SECURE) ───────────────────────────────────
    def _create_admin(self):
        username = os.getenv("DJANGO_ADMIN_USERNAME", "admin")
        email = os.getenv("DJANGO_ADMIN_EMAIL", "admin@prepedge.com")
        password = os.getenv("DJANGO_ADMIN_PASSWORD")

        if not password:
            self.stdout.write(self.style.WARNING(
                "⚠️ DJANGO_ADMIN_PASSWORD not set → Admin not created"
            ))
            return

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password)
            self.stdout.write('  Admin user created')
        else:
            self.stdout.write('  Admin already exists — skipped')

    # ── 3. Demo student (SAFE) ───────────────────────────────────
    def _create_demo_student(self):
        from app1.models import Subscription, UserProfile, UserProgress, TestResult

        password = os.getenv("DJANGO_STUDENT_PASSWORD", "student123")

        user, created = User.objects.get_or_create(
            username='student',
            defaults={
                'email': 'student@prepedge.com',
                'first_name': 'Demo',
                'last_name': 'Student',
            }
        )

        if created:
            user.set_password(password)
            user.save()

        # Profile
        UserProfile.objects.get_or_create(
            user=user,
            defaults={'bio': 'Demo student account'}
        )

        # Subscription
        Subscription.objects.get_or_create(
            user=user,
            defaults={'plan': 'free', 'status': 'active'},
        )

        # Progress
        progress_items = [
            ('python', 'Python Basics', 'lesson', True),
            ('python', 'Control Flow', 'lesson', True),
            ('python', 'Functions', 'lesson', False),
            ('python', 'Basics Practice', 'practice', True),
            ('java', 'Java Basics', 'lesson', True),
            ('dsa', 'DSA Basics', 'lesson', False),
        ]

        for module, topic, ctype, done in progress_items:
            UserProgress.objects.get_or_create(
                user=user,
                module=module,
                topic_name=topic,
                content_type=ctype,
                defaults={
                    'completed': done,
                    'completed_at': timezone.now() if done else None
                },
            )

        # Test results
        test_items = [
            ('python', 'Python Test', 72.0, 4, 3),
            ('java', 'Java Test', 55.0, 10, 5),
            ('dsa', 'DSA Test', 40.0, 15, 6),
            ('sql', 'SQL Test', 85.0, 5, 4),
        ]

        for module, name, score, total, correct in test_items:
            if not TestResult.objects.filter(user=user, test_name=name).exists():
                TestResult.objects.create(
                    user=user,
                    module=module,
                    test_name=name,
                    score=score,
                    total_questions=total,
                    correct_answers=correct,
                )

        status = 'created' if created else 'already exists — updated'
        self.stdout.write(f'  Student user {status}')