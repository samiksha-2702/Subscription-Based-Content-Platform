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
    return render(request, 'java/javainfo.html')

def cpp_info(request):
    return render(request, 'cpp/cppinfo.html')

def js_info(request):
    return render(request, 'js/javasinfo.html')

def sql_info(request):
    return render(request, 'sql/sql_info.html')

def dsa_info(request):
    return render(request, 'dsa.html')
# CHEAT SHEETS
def python_basics(request):
    return render(request, 'pythonbasics.html')

def control_flow(request):
    return render(request, 'control_flow.html')

def python_functions(request):
    return render(request, 'functionspython.html')


# ARTICLES
def python_interview(request):
    return render(request, 'pythoninterview.html')

def python_comparison(request):
    return render(request, 'pythoncomparision.html')

def python_libraries(request):
    return render(request, 'pythonlibraries.html')


# PRACTICE
def py_basics_practice(request):
    return render(request, 'pybasicspractice.html')

def py_loop_practice(request):
    return render(request, 'pylooppractice.html')

def py_function_practice(request):
    return render(request, 'pyfunctionpractice.html')


# TEST
def python_test(request):
    return render(request, 'python_test.html')

#java
# Cheat Sheet Pages
def java_basics(request):
    return render(request, "java/java_basics.html")


def java_control(request):
    return render(request, "java/java_control.html")


def java_oop(request):
    return render(request, "java/java_oop.html")


# Articles
def java_interview(request):
    return render(request, "java/java_interview.html")


def java_vs_python(request):
    return render(request, "java/java_vs_languages.html")


def springboot(request):
    return render(request, "java/springboot.html")


# Practice Pages
def java_basic_practice(request):
    return render(request, "java/java_basic_practice.html")


def java_loop_practice(request):
    return render(request, "java/java_loop_practice.html")


def java_oop_practice(request):
    return render(request, "java/java_oop_practice.html")


# Test Page
def java_test(request):
    return render(request, "java/java_test.html")
 
 
 #CPP
def cpp_basics(request):
    return render(request, "cpp/cpp_basics.html")

def cpp_control(request):
    return render(request, "cpp/cpp_control.html")

def cpp_oop(request):
    return render(request, "cpp/cpp_oop.html")

def cpp_practice(request):
    return render(request, "cpp/cpp_practice.html")

def cpp_test(request):
    return render(request, "cpp/cpp_test.html")
#JS
def js_basics(request):
    return render(request, 'js/js_basics.html')

def js_control(request):
    return render(request, 'js/js_control.html')

def js_dom(request):
    return render(request, 'js/js_dom.html')

def js_es6(request):
    return render(request, 'js/js_es6.html')

def js_practice(request):
    return render(request, 'js/js_practice.html')

def js_test(request):
    return render(request, 'js/js_test.html')
#sql
def sql_basics(request):
    return render(request,'sql/sql_basics.html')

def sql_queries(request):
    return render(request,'sql/sql_queries.html')

def sql_joins(request):
    return render(request,'sql/sql_joins.html')

def sql_advanced(request):
    return render(request,'sql/sql_advanced.html')

def sql_practice(request):
    return render(request,'sql/sql_practice.html')

def sql_test(request):
    return render(request,'sql/sql_test.html')


# Experts
def live_session_register(request):
    return render(request, "expert/live_session_register.html")
def expert_profile(request):
    return render(request, "expert/expert_profile.html")