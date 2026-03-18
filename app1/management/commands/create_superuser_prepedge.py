"""
python manage.py create_superuser_prepedge

Creates the PrepEdge superuser with a single command.
No prompts needed — just run and go.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create the PrepEdge admin superuser (username: admin, password: admin123)'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--email',    default='admin@prepedge.com')
        parser.add_argument('--password', default='admin123')

    def handle(self, *args, **options):
        username = options['username']
        email    = options['email']
        password = options['password']

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(
                    f'  ⚠️  Superuser "{username}" already exists. '
                    f'Visit /admin/ and log in with your existing password.'
                )
            )
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        # Also create profile + subscription for the admin
        from app1.models import UserProfile, Subscription
        from django.contrib.auth.models import User as U
        user = U.objects.get(username=username)
        UserProfile.objects.get_or_create(user=user)
        Subscription.objects.get_or_create(
            user=user,
            defaults={'plan': 'premium', 'status': 'active'}
        )

        self.stdout.write(self.style.SUCCESS(
            f'\n✅  Superuser created!\n'
            f'    Username : {username}\n'
            f'    Password : {password}\n'
            f'    Email    : {email}\n'
            f'    URL      : http://127.0.0.1:8000/admin/\n'
        ))
