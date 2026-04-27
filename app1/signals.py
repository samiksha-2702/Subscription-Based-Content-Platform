from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import LoginHistory

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    LoginHistory.objects.create(
        user=user,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT')
    )