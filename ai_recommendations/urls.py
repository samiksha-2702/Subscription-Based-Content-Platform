from django.urls import path
from . import views        # adjust import to match your app structure
 
urlpatterns = [
    # Dashboard – main recommendations page
    path('dashboard/',          views.ai_dashboard,            name='ai_dashboard'),
 
    # Refresh recommendations (POST)
    path('refresh/',            views.refresh_recommendations, name='ai_refresh'),
 
    # Dismiss a single recommendation (POST)
    path('dismiss/<int:rec_id>/', views.dismiss_recommendation, name='ai_dismiss'),
 
    # Weak areas breakdown
    path('weak-areas/',         views.weak_areas_detail,       name='ai_weak_areas'),
 
    # Learning path
    path('learning-path/',      views.learning_path,           name='ai_learning_path'),
 
    # JSON API for widgets
    path('api/recommendations/', views.recommendations_api,    name='ai_recommendations_api'),

      # AJAX endpoint — test pages post score here after JS grading
    path('record-score/',        views.record_score,            name='ai_record_score'),
]
 