from django.urls import path
from .views import ai_coach_response

urlpatterns = [
    path('ask/', ai_coach_response, name='ai_coach'),
]