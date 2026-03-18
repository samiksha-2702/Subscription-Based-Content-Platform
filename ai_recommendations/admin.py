from django.contrib import admin
from .models import (
    Topic, UserQuizAttempt, UserPracticeCompletion,
    UserWeakArea, UserRecommendation
)
 
 
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display    = ['name', 'module', 'difficulty', 'slug']
    list_filter     = ['module', 'difficulty']
    search_fields   = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['prerequisites']
 
 
@admin.register(UserQuizAttempt)
class UserQuizAttemptAdmin(admin.ModelAdmin):
    list_display  = ['user', 'topic', 'score', 'passed', 'attempted_at']
    list_filter   = ['topic__module', 'attempted_at']
    search_fields = ['user__username', 'topic__name']
    readonly_fields = ['attempted_at']
 
    @admin.display(boolean=True)
    def passed(self, obj):
        return obj.passed
 
 
@admin.register(UserPracticeCompletion)
class UserPracticeCompletionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'topic', 'exercise_count', 'completed_at']
    list_filter   = ['topic__module']
    search_fields = ['user__username', 'topic__name']
 
 
@admin.register(UserWeakArea)
class UserWeakAreaAdmin(admin.ModelAdmin):
    list_display  = ['user', 'topic', 'weakness_score_display', 'reason', 'last_updated']
    list_filter   = ['topic__module']
    search_fields = ['user__username', 'topic__name']
    ordering      = ['-weakness_score']
 
    def weakness_score_display(self, obj):
        pct = obj.weakness_score * 100
        if pct >= 70:
            emoji = "🔴"
        elif pct >= 40:
            emoji = "🟡"
        else:
            emoji = "🟢"
        return f"{emoji} {pct:.0f}%"
    weakness_score_display.short_description = 'Weakness'
 
 
@admin.register(UserRecommendation)
class UserRecommendationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'rec_type', 'title', 'priority', 'is_dismissed', 'created_at']
    list_filter   = ['rec_type', 'is_dismissed', 'created_at']
    search_fields = ['user__username', 'title']
    actions       = ['mark_dismissed', 'mark_active']
 
    @admin.action(description='Mark selected as dismissed')
    def mark_dismissed(self, request, queryset):
        queryset.update(is_dismissed=True)
 
    @admin.action(description='Mark selected as active')
    def mark_active(self, request, queryset):
        queryset.update(is_dismissed=False)
 
