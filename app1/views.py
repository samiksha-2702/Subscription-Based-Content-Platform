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


# -----------------------------
# Authentication
# -----------------------------

def register_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        messages.success(request, "Registration successful")
        return redirect('login')

    return render(request, 'register.html')


def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')