from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout


# -----------------------------
# Main Pages
# -----------------------------

def index(request):
    return render(request, 'index.html')


def programming(request):
    return render(request, 'programming.html')


def company(request):
    return render(request, 'company.html')


def communication(request):
    return render(request, 'communication_softskills.html')


def aptitude(request):
    return render(request, 'aptitude.html')


def ai_recommendation(request):
    return render(request, 'ai_recommendation.html')


from django.shortcuts import render

def index(request):
    return render(request, 'index.html')

def programming(request):
    return render(request, 'programming.html')

def company(request):
    return render(request, 'company.html')

def expert_talks(request):
    return render(request, 'expert_talks.html')

def communication(request):
    return render(request, 'communication/comm.html')

def aptitude(request):
    return render(request, 'questions.html')

def ai_recommendation(request):
    return render(request, 'ai.html')

def login_view(request):
    return render(request, 'login.html')

def register_view(request):
    return render(request, 'register.html')

def plans(request):
    return render(request, 'plans.html')

def programming_home(request):
    return render(request, 'programming.html')

def python_info(request):
    return render(request, 'pythoninfo.html')

def java_info(request):
    return render(request, 'javainfo.html')

def cpp_info(request):
    return render(request, 'cppinfo.html')

def js_info(request):
    return render(request, 'jsinfo.html')

def sql_info(request):
    return render(request, 'sql.html')

def dsa_info(request):
    return render(request, 'dsa.html')