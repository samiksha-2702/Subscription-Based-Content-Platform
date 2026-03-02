"""
URL configuration for prepedge project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from app1 import views

urlpatterns = [
    path('', views.index, name='index'),
    path('programming/', views.programming, name='programming'),
    path('company/', views.company, name='company'),
    path('expert-talks/', views.expert_talks, name='expert_talks'),
    path('communication/', views.communication, name='communication'),
    path('aptitude/', views.aptitude, name='aptitude'),
    path('ai/', views.ai_recommendation, name='ai'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('plans/', views.plans, name='plans'),
    path('', views.programming_home, name='programming_home'),

    path('python/', views.python_info, name='python_info'),
    path('java/', views.java_info, name='java_info'),
    path('cpp/', views.cpp_info, name='cpp_info'),
    path('javascript/', views.js_info, name='js_info'),
    path('sql/', views.sql_info, name='sql_info'),
    path('dsa/', views.dsa_info, name='dsa_info'),
]