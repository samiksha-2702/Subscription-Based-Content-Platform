from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models

from django.db import models

class UserProfile(models.Model):
    username = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    password = models.CharField(max_length=255)

    def __str__(self):
        return self.username
# ══════════════════════════════════════════════════════════════════
# 1. USER PROFILE
# ══════════════════════════════════════════════════════════════════

class UserProfile(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio        = models.TextField(blank=True, default='')
    avatar_url = models.URLField(blank=True, default='')
    phone      = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Profile'

    def __str__(self):
        return f"Profile — {self.user.username}"


# ══════════════════════════════════════════════════════════════════
# 2. LOGIN HISTORY
#    Every successful login is recorded here
# ══════════════════════════════════════════════════════════════════

class LoginHistory(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    logged_in_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-logged_in_at']
        verbose_name        = 'Login History'
        verbose_name_plural = 'Login Histories'

    def __str__(self):
        return f"{self.user.username} — {self.logged_in_at.strftime('%d %b %Y %H:%M')}"


# ══════════════════════════════════════════════════════════════════
# 3. SUBSCRIPTION
# ══════════════════════════════════════════════════════════════════

class Subscription(models.Model):
    PLAN_CHOICES = [
        ('free',    'Free'),
        ('premium', 'Premium'),
    ]
    STATUS_CHOICES = [
        ('active',    'Active'),
        ('expired',   'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan       = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    notes      = models.TextField(blank=True, default='')   # admin notes

    class Meta:
        verbose_name = 'Subscription'

    def __str__(self):
        return f"{self.user.username} — {self.plan} ({self.status})"

    @property
    def is_active(self):
        if self.status != 'active':
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    @property
    def is_premium(self):
        return self.plan == 'premium' and self.is_active


# ══════════════════════════════════════════════════════════════════
# 4. PAYMENT RECORD
#    Every payment attempt (success or fail) is stored here
# ══════════════════════════════════════════════════════════════════

class PaymentRecord(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('success',   'Success'),
        ('failed',    'Failed'),
        ('refunded',  'Refunded'),
    ]
    METHOD_CHOICES = [
        ('card',   'Credit / Debit Card'),
        ('upi',    'UPI'),
        ('wallet', 'Wallet'),
        ('other',  'Other'),
    ]

    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    plan           = models.CharField(max_length=20, default='premium')
    amount         = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    currency       = models.CharField(max_length=5, default='INR')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    method         = models.CharField(max_length=20, choices=METHOD_CHOICES, default='card')
    transaction_id = models.CharField(max_length=200, blank=True, default='')
    paid_at        = models.DateTimeField(auto_now_add=True)
    notes          = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-paid_at']
        verbose_name = 'Payment Record'

    def __str__(self):
        return f"{self.user.username} | ₹{self.amount} | {self.status} | {self.paid_at.strftime('%d %b %Y')}"


# ══════════════════════════════════════════════════════════════════
# 5. LIVE SESSION
# ══════════════════════════════════════════════════════════════════

class LiveSession(models.Model):
    title        = models.CharField(max_length=200)
    description  = models.TextField(blank=True)
    session_date = models.DateTimeField()
    created_at   = models.DateTimeField(auto_now_add=True)
    is_active    = models.BooleanField(default=True)

    class Meta:
        ordering = ['session_date']
        verbose_name = 'Live Session'

    def __str__(self):
        return f"{self.title} — {self.session_date.strftime('%d %b %Y')}"


class LiveSessionRegistration(models.Model):
    user         = models.ForeignKey(User, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='session_registrations')
    session_name = models.CharField(max_length=200)
    name         = models.CharField(max_length=150)
    email        = models.EmailField()
    message      = models.TextField(blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-registered_at']
        verbose_name = 'Session Registration'

    def __str__(self):
        return f"{self.name} → {self.session_name}"


# ══════════════════════════════════════════════════════════════════
# 6. USER PROGRESS
# ══════════════════════════════════════════════════════════════════

class UserProgress(models.Model):
    MODULE_CHOICES = [
        ('python','Python'), ('java','Java'), ('cpp','C++'),
        ('javascript','JavaScript'), ('sql','SQL'), ('dsa','DSA'),
        ('communication','Communication'), ('aptitude','Aptitude'),
    ]
    TYPE_CHOICES = [
        ('lesson','Lesson'), ('practice','Practice'), ('test','Test'),
    ]

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    module       = models.CharField(max_length=30, choices=MODULE_CHOICES)
    topic_name   = models.CharField(max_length=200)
    content_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='lesson')
    completed    = models.BooleanField(default=False)
    visited_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'module', 'topic_name', 'content_type')
        ordering = ['-visited_at']
        verbose_name = 'User Progress'

    def __str__(self):
        status = '✅' if self.completed else '🔄'
        return f"{status} {self.user.username} — {self.module}/{self.topic_name}"


# ══════════════════════════════════════════════════════════════════
# 7. TEST RESULT
# ══════════════════════════════════════════════════════════════════

class TestResult(models.Model):
    MODULE_CHOICES = [
        ('python','Python'), ('java','Java'), ('cpp','C++'),
        ('javascript','JavaScript'), ('sql','SQL'), ('dsa','DSA'),
        ('communication','Communication'), ('aptitude','Aptitude'),
        ('interview','Interview'), ('technical','Technical'),
    ]

    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results')
    module          = models.CharField(max_length=30, choices=MODULE_CHOICES)
    test_name       = models.CharField(max_length=200)
    score           = models.FloatField()
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    time_taken      = models.PositiveIntegerField(default=0)
    attempted_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempted_at']
        verbose_name = 'Test Result'

    def __str__(self):
        return f"{self.user.username} | {self.test_name} | {self.score:.1f}%"

    @property
    def passed(self):
        return self.score >= 60.0

    @property
    def grade(self):
        if self.score >= 90: return 'A'
        if self.score >= 75: return 'B'
        if self.score >= 60: return 'C'
        return 'F'


# ══════════════════════════════════════════════════════════════════
# 8. CONTACT / FEEDBACK
# ══════════════════════════════════════════════════════════════════

class ContactMessage(models.Model):
    name     = models.CharField(max_length=150)
    email    = models.EmailField()
    subject  = models.CharField(max_length=300, blank=True)
    message  = models.TextField()
    sent_at  = models.DateTimeField(auto_now_add=True)
    is_read  = models.BooleanField(default=False)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Contact Message'

    def __str__(self):
        return f"{self.name} — {self.subject[:50]}"