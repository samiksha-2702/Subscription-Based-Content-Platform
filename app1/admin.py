from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import Count, Avg
from django.utils import timezone
from .models import (
    UserProfile, LoginHistory, Subscription, PaymentRecord,
    LiveSession, LiveSessionRegistration,
    UserProgress, TestResult, ContactMessage,
)
from .models import Test
from .models import Feedback

admin.site.register(Feedback)
admin.site.register(Test)
# ══════════════════════════════════════════════════════════════════
# SITE HEADER
# ══════════════════════════════════════════════════════════════════
admin.site.site_header  = '🎯 PrepEdge Admin Panel'
admin.site.site_title   = 'PrepEdge Admin'
admin.site.index_title  = 'Welcome to PrepEdge Dashboard'


# ══════════════════════════════════════════════════════════════════
# INLINES  (shown inside the User change page)
# ══════════════════════════════════════════════════════════════════

class UserProfileInline(admin.StackedInline):
    model               = UserProfile
    can_delete          = False
    verbose_name_plural = 'Profile'
    fields              = ['bio', 'phone', 'avatar_url']
    extra               = 0


class SubscriptionInline(admin.StackedInline):
    model               = Subscription
    can_delete          = False
    verbose_name_plural = 'Subscription'
    fields              = ['plan', 'status', 'expires_at', 'notes']
    extra               = 0


class PaymentInline(admin.TabularInline):
    model               = PaymentRecord
    extra               = 0
    readonly_fields     = ['amount', 'currency', 'plan', 'status', 'method',
                           'transaction_id', 'paid_at']
    fields              = ['plan', 'amount', 'currency', 'method', 'status',
                           'transaction_id', 'paid_at']
    can_delete          = False
    verbose_name_plural = 'Payment History'
    max_num             = 0   # read-only — no adding payments from here


class LoginHistoryInline(admin.TabularInline):
    model               = LoginHistory
    extra               = 0
    readonly_fields     = ['logged_in_at', 'ip_address', 'user_agent']
    fields              = ['logged_in_at', 'ip_address', 'user_agent']
    can_delete          = False
    verbose_name_plural = 'Login History (last 10)'
    max_num             = 0

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-logged_in_at')[:10]


# ══════════════════════════════════════════════════════════════════
# EXTENDED USER ADMIN
# Shows profile + subscription + payments + login history
# all on the same User page
# ══════════════════════════════════════════════════════════════════

class ExtendedUserAdmin(BaseUserAdmin):
    inlines     = [UserProfileInline, SubscriptionInline,
                   PaymentInline, LoginHistoryInline]

    list_display = ['username', 'email', 'full_name', 'plan_badge',
                    'is_active', 'total_tests', 'date_joined']

    list_filter  = BaseUserAdmin.list_filter + ('subscription__plan', 'subscription__status')

    search_fields = ['username', 'email', 'first_name', 'last_name']

    # ── Custom columns ──────────────────────────────────────────
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or '—'
    full_name.short_description = 'Name'

    def plan_badge(self, obj):
        try:
            plan = obj.subscription.plan
            if plan == 'premium':
                return format_html(
    '<span style="background:#6b7280;color:#fff;padding:2px 10px;'
    'border-radius:6px;font-size:11px;">{}</span>',
    'FREE'
)
        except Exception:
            pass
        return format_html(
    '<span style="background:#6b7280;color:#fff;padding:2px 10px;'
    'border-radius:6px;font-size:11px;">{}</span>',
    'FREE'
)
        
    plan_badge.short_description = 'Plan'

    def total_tests(self, obj):
        count = obj.test_results.count()
        return count if count else '—'
    total_tests.short_description = 'Tests'

    # ── Bulk actions ────────────────────────────────────────────
    actions = ['make_premium', 'make_free', 'deactivate_users', 'activate_users']

    @admin.action(description='⭐ Upgrade selected users to Premium')
    def make_premium(self, request, queryset):
        for user in queryset:
            Subscription.objects.update_or_create(
                user=user,
                defaults={'plan': 'premium', 'status': 'active'}
            )
        self.message_user(request, f'{queryset.count()} user(s) upgraded to Premium.')

    @admin.action(description='Revert selected users to Free plan')
    def make_free(self, request, queryset):
        for user in queryset:
            Subscription.objects.update_or_create(
                user=user, defaults={'plan': 'free'}
            )
        self.message_user(request, f'{queryset.count()} user(s) reverted to Free.')

    @admin.action(description='🚫 Deactivate selected users')
    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} user(s) deactivated.')

    @admin.action(description='✅ Activate selected users')
    def activate_users(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} user(s) activated.')


admin.site.unregister(User)
admin.site.register(User, ExtendedUserAdmin)


# ══════════════════════════════════════════════════════════════════
# LOGIN HISTORY
# ══════════════════════════════════════════════════════════════════

@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display    = ['user', 'ip_address', 'logged_in_at', 'user_agent_short']
    list_filter     = ['logged_in_at']
    search_fields   = ['user__username', 'ip_address']
    readonly_fields = ['user', 'ip_address', 'user_agent', 'logged_in_at']
    ordering        = ['-logged_in_at']

    def user_agent_short(self, obj):
        return obj.user_agent[:60] + '…' if len(obj.user_agent) > 60 else obj.user_agent
    user_agent_short.short_description = 'Browser / Device'

    def has_add_permission(self, request):
        return False   # login history is auto-recorded, never manually added


# ══════════════════════════════════════════════════════════════════
# SUBSCRIPTION
# ══════════════════════════════════════════════════════════════════

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'email', 'plan_badge', 'status_badge',
                     'started_at', 'expires_at', 'days_remaining']
    list_filter   = ['plan', 'status']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['started_at']
    fields        = ['user', 'plan', 'status', 'started_at', 'expires_at', 'notes']

    actions = ['activate_premium', 'revert_to_free', 'mark_expired', 'mark_cancelled']

    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'

    def plan_badge(self, obj):
        try:
            if obj.subscription.plan == 'premium':
             return "⭐ PREMIUM"
        except:
            pass
        return "FREE"

    def status_badge(self, obj):
        colours = {'active': '#22c55e', 'expired': '#ef4444', 'cancelled': '#6b7280'}
        colour = colours.get(obj.status, '#6b7280')
        return format_html(
            '<span style="color:{}; font-weight:600;">{}</span>',
            colour, obj.status.capitalize()
        )
    status_badge.short_description = 'Status'

    def days_remaining(self, obj):
        if not obj.expires_at:
            return '∞ Lifetime'
        delta = (obj.expires_at - timezone.now()).days
        if delta < 0:
            return format_html('<span style="color:#ef4444;">Expired</span>')
        return f'{delta} days'
    days_remaining.short_description = 'Remaining'

    @admin.action(description='⭐ Activate Premium for selected')
    def activate_premium(self, request, queryset):
        queryset.update(plan='premium', status='active')
        self.message_user(request, f'{queryset.count()} subscription(s) upgraded to Premium.')

    @admin.action(description='Revert selected to Free')
    def revert_to_free(self, request, queryset):
        queryset.update(plan='free')
        self.message_user(request, f'{queryset.count()} subscription(s) reverted to Free.')

    @admin.action(description='Mark selected as Expired')
    def mark_expired(self, request, queryset):
        queryset.update(status='expired')

    @admin.action(description='Mark selected as Cancelled')
    def mark_cancelled(self, request, queryset):
        queryset.update(status='cancelled')


# ══════════════════════════════════════════════════════════════════
# PAYMENT RECORDS
# ══════════════════════════════════════════════════════════════════

@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display  = ['user', 'email', 'amount_display', 'plan',
                     'method', 'status_badge', 'transaction_id', 'paid_at']
    list_filter   = ['status', 'plan', 'method', 'paid_at']
    search_fields = ['user__username', 'user__email', 'transaction_id']
    readonly_fields = ['paid_at']
    ordering      = ['-paid_at']

    fieldsets = (
        ('User & Plan', {
            'fields': ('user', 'plan')
        }),
        ('Payment Details', {
            'fields': ('amount', 'currency', 'method', 'transaction_id')
        }),
        ('Status', {
            'fields': ('status', 'notes', 'paid_at')
        }),
    )

    actions = ['mark_success', 'mark_refunded', 'mark_failed',
                'approve_and_upgrade_subscription']

    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'

    def amount_display(self, obj):
        return f'₹{obj.amount}'
    amount_display.short_description = 'Amount'

    def status_badge(self, obj):
        colours = {
            'success':  '#22c55e',
            'pending':  '#f59e0b',
            'failed':   '#ef4444',
            'refunded': '#6b7280',
        }
        colour = colours.get(obj.status, '#6b7280')
        icons  = {'success':'✅','pending':'⏳','failed':'❌','refunded':'↩️'}
        icon   = icons.get(obj.status, '')
        return format_html(
            '<span style="color:{};font-weight:600;">{} {}</span>',
            colour, icon, obj.status.capitalize()
        )
    status_badge.short_description = 'Status'

    @admin.action(description='✅ Mark selected payments as Successful')
    def mark_success(self, request, queryset):
        queryset.update(status='success')
        self.message_user(request, f'{queryset.count()} payment(s) marked successful.')

    @admin.action(description='↩️ Mark selected payments as Refunded')
    def mark_refunded(self, request, queryset):
        queryset.update(status='refunded')

    @admin.action(description='❌ Mark selected payments as Failed')
    def mark_failed(self, request, queryset):
        queryset.update(status='failed')

    @admin.action(description='⭐ Approve payment AND upgrade user subscription')
    def approve_and_upgrade_subscription(self, request, queryset):
        upgraded = 0
        for payment in queryset:
            payment.status = 'success'
            payment.save()
            Subscription.objects.update_or_create(
                user=payment.user,
                defaults={'plan': 'premium', 'status': 'active'}
            )
            upgraded += 1
        self.message_user(
            request,
            f'{upgraded} payment(s) approved and {upgraded} user(s) upgraded to Premium.'
        )


# ══════════════════════════════════════════════════════════════════
# LIVE SESSIONS
# ══════════════════════════════════════════════════════════════════

@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display  = ['title', 'session_date', 'is_active', 'registrations_count']
    list_filter   = ['is_active', 'session_date']
    search_fields = ['title', 'description']

    def registrations_count(self, obj):
        return LiveSessionRegistration.objects.filter(session_name=obj.title).count()
    registrations_count.short_description = 'Registrations'


@admin.register(LiveSessionRegistration)
class LiveSessionRegistrationAdmin(admin.ModelAdmin):
    list_display    = ['name', 'email', 'session_name', 'user', 'registered_at']
    list_filter     = ['session_name', 'registered_at']
    search_fields   = ['name', 'email', 'session_name', 'user__username']
    readonly_fields = ['registered_at']


# ══════════════════════════════════════════════════════════════════
# USER PROGRESS
# ══════════════════════════════════════════════════════════════════

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display  = ['user', 'module', 'topic_name', 'content_type',
                     'completed_badge', 'visited_at']
    list_filter   = ['module', 'content_type', 'completed']
    search_fields = ['user__username', 'topic_name']

    def completed_badge(self, obj):
        if obj.completed:
            return format_html('<span style="color:#22c55e;font-weight:700;">✅ Done</span>')
        return format_html('<span style="color:{};">{}</span>', '#f59e0b', '🔄 In Progress')
    completed_badge.short_description = 'Status'


# ══════════════════════════════════════════════════════════════════
# TEST RESULTS
# ══════════════════════════════════════════════════════════════════

@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'test', 'score_bar', 'grade_badge', 'passed_badge', 'date_attempted']
    list_filter = ['test', 'date_attempted']
    search_fields = ['user__username', 'test__name']
    ordering = ['-date_attempted']
    readonly_fields = ['date_attempted']

    def score_bar(self, obj):
        colour = '#22c55e' if obj.score >= 60 else '#ef4444'
        return format_html(
            '<div style="background:#1e293b;border-radius:4px;width:120px;height:14px;">'
            '<div style="background:{};width:{}%;height:100%;border-radius:4px;"></div>'
            '</div> <small>{}%</small>',
            colour, min(obj.score, 100), obj.score
        )

    def grade_badge(self, obj):
        colours = {'A':'#22c55e','B':'#3b82f6','C':'#f59e0b','F':'#ef4444'}
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;">{}</span>',
            colours.get(obj.grade,'#6b7280'), obj.grade
        )

    @admin.display(boolean=True)
    def passed_badge(self, obj):
        return obj.passed

# ══════════════════════════════════════════════════════════════════
# CONTACT MESSAGES
# ══════════════════════════════════════════════════════════════════

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display  = ['name', 'email', 'subject', 'read_badge', 'sent_at']
    list_filter   = ['is_read', 'sent_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['sent_at']
    actions       = ['mark_read', 'mark_unread']

    def read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color:#22c55e;">✅ Read</span>')
        return format_html('<span style="color:#f59e0b;font-weight:700;">🔴 Unread</span>')
    read_badge.short_description = 'Status'

    @admin.action(description='Mark selected as Read')
    def mark_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description='Mark selected as Unread')
    def mark_unread(self, request, queryset):
        queryset.update(is_read=False)