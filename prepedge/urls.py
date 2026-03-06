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
    path('java/', views.java_info, name='javainfo'),
    path('cpp/', views.cpp_info, name='cpp_info'),
    path('javascript/', views.js_info, name='js_info'),
    path('sql/', views.sql_info, name='sql_info'),
    path('dsa/', views.dsa_info, name='dsa_info'),
     # CHEAT SHEETS
    path('python/basics/', views.python_basics, name='pythonbasics'),
    path('python/control-flow/', views.control_flow, name='control_flow'),
    path('python/functions/', views.python_functions, name='functionspython'),

    # ARTICLES
    path('python/interview/', views.python_interview, name='pythoninterview'),
    path('python/comparison/', views.python_comparison, name='pythoncomparision'),
    path('python/libraries/', views.python_libraries, name='pythonlibraries'),

    # PRACTICE
    path('python/practice-basics/', views.py_basics_practice, name='pybasicspractice'),
    path('python/practice-loops/', views.py_loop_practice, name='pylooppractice'),
    path('python/practice-functions/', views.py_function_practice, name='pyfunctionpractice'),

    # TEST
    path('python/test/', views.python_test, name='python_test'),
    #JAVA
    path('java-basics/', views.java_basics, name='java_basics'),
    path('java-control/', views.java_control, name='java_control'),
    path('java-oop/', views.java_oop, name='java_oop'),
    path('java-interview/', views.java_interview, name='java_interview'),
    path('java-vs-python/', views.java_vs_python, name='java_vs_languages'),
    path('springboot/', views.springboot, name='springboot'),
    path('java-basic-practice/', views.java_basic_practice, name='java_basic_practice'),
    path('java-loop-practice/', views.java_loop_practice, name='java_loop_practice'),
    path('java-oop-practice/', views.java_oop_practice, name='java_oop_practice'),
    path('java-test/', views.java_test, name='java_test'),
]