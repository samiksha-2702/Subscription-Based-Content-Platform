from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from .models import UserProfile
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from .models import TestResult, Test , Subscription
from django.shortcuts import render, get_object_or_404 , redirect
from django.http import JsonResponse
from django.urls import reverse
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg


def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")

        # 1. Password match check
        if password != password2:
            return render(request, "register.html", {"error": "Passwords do not match"})

        # 2. Username exists check
        if User.objects.filter(username=username).exists():
            return render(request, "register.html", {"error": "Username already exists"})

        # 3. Create User
        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            first_name=full_name
        )

        # 4. Create Profile
        UserProfile.objects.create(user=user)

        # 5. Redirect to login
        return redirect("login")

    return render(request, "register.html")

#login
def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            print("LOGIN SUCCESS")  # check terminal
            login(request, user)
            return redirect("plans") # or dashboard
        else:
            return render(request, "login.html", {
                "error": "Invalid username or password",
                "username": username
            })
        
    return render(request, "login.html")
@login_required
def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    user = request.user

    results = TestResult.objects.filter(user=user)

    total_tests = results.count()

    # ✅ Use marks instead of score
    avg_score = results.aggregate(avg=Avg('marks'))['avg'] or 0

    last_active = results.order_by('-date_attempted').first()

    subscription = Subscription.objects.filter(user=user).first()

    context = {
        'total_tests': total_tests,
        'avg_score': round(avg_score, 2),
        'last_active': last_active.date_attempted if last_active else None,
        'subscription': subscription,
        'results': results
    }

    return render(request, 'profile.html', context)
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _get_subscription(user):
    """Return the user's Subscription, creating a free one if missing."""
    if not user.is_authenticated:
        return None
    from .models import Subscription
    sub, _ = Subscription.objects.get_or_create(
        user=user,
        defaults={'plan': 'free', 'status': 'active'}
    )
    return sub


def _ensure_profile(user):
    """Create UserProfile if it doesn't exist yet."""
    from .models import UserProfile
    UserProfile.objects.get_or_create(user=user)


def _mark_progress(user, module, topic_name, content_type='lesson', completed=False):
    """Record that a user visited / completed a topic page."""
    if not user.is_authenticated:
        return
    from .models import UserProgress
    obj, created = UserProgress.objects.get_or_create(
        user=user, module=module,
        topic_name=topic_name, content_type=content_type,
    )
    if completed and not obj.completed:
        obj.completed = True
        obj.completed_at = timezone.now()
        obj.save()


def _save_test_result(user, module, test_name, score_pct,
                      total_q=0, correct=0, time_sec=0):

    if not user.is_authenticated:
        return

    from .models import TestResult, Test

    # ✅ Get actual Test object
    test = Test.objects.filter(name=test_name).first()

    # ✅ Calculate marks if not given
    if total_q > 0 and correct > 0:
        score_pct = (correct / total_q) * 100

    result = TestResult.objects.create(
        user=user,
        test=test,                    # ✅ correct field
        total_questions=total_q,
        correct_answers=correct,
        marks=score_pct,             # ✅ IMPORTANT FIX
        time_taken=time_sec,
    )

    # AI recommendation (keep same)
    SLUG_MAP = {
        'python': 'python-basics',
        'java': 'java-basics',
        'cpp': 'cpp-basics',
        'javascript': 'js-basics',
        'sql': 'sql-basics',
        'dsa': 'dsa-basics',
        'communication': 'comm-interview',
        'aptitude': 'comm-interview',
    }

    slug = SLUG_MAP.get(module)

    if slug:
        try:
            from ai_recommendations.views import record_quiz_attempt
            record_quiz_attempt(user, slug, score_pct)
        except Exception:
            pass

    return result


# ══════════════════════════════════════════════════════════════════
# MAIN PAGES
# ══════════════════════════════════════════════════════════════════

def index(request):
    return render(request, 'index.html')
def home(request):
    return render(request, 'home.html')
@login_required
def programming(request):
    return render(request, 'programming.html')
@login_required
def company(request):
    return render(request, 'company.html')
@login_required
def expert_talks(request):
    return render(request, 'expert/expert.html')
@login_required
def communication(request):
    return render(request, 'communication/comm.html')
@login_required
def aptitude(request):
    sub = _get_subscription(request.user)
    return render(request, 'questions.html', {
        'subscribed': sub.is_premium if sub else False
    })
@login_required
def ai_recommendation(request):
    return render(request, 'ai.html')
@login_required
def plans(request):
    return render(request, 'plans.html')
@login_required
def subscribe(request):
    return render(request, 'plans.html')
@login_required
def programming_home(request):
    return render(request, 'programming.html')


# ══════════════════════════════════════════════════════════════════
# LIVE SESSION REGISTRATION
# ══════════════════════════════════════════════════════════════════

def live_session_register(request):
    success = False
    if request.method == 'POST':
        from .models import LiveSessionRegistration
        name    = request.POST.get('name', '').strip()
        email   = request.POST.get('email', '').strip()
        session = request.POST.get('session', '').strip()
        message_text = request.POST.get('message', '').strip()
        if name and email and session:
            LiveSessionRegistration.objects.create(
                user         = request.user if request.user.is_authenticated else None,
                name         = name,
                email        = email,
                session_name = session,
                message      = message_text,
            )
            success = True
    return render(request, 'expert/live-session-regest.html', {'success': success})

def view_talks(request):
    return render(request, 'expert/view-talks.html')


# ══════════════════════════════════════════════════════════════════
# PYTHON MODULE
# ══════════════════════════════════════════════════════════════════

def python_info(request):
    _mark_progress(request.user, 'python', 'Python Info')
    return render(request, 'pythoninfo.html')

def python_basics(request):
    _mark_progress(request.user, 'python', 'Python Basics')
    return render(request, 'pythonbasics.html')

def control_flow(request):
    _mark_progress(request.user, 'python', 'Control Flow')
    return render(request, 'control_flow.html')

def python_functions(request):
    _mark_progress(request.user, 'python', 'Functions')
    return render(request, 'functionspython.html')

def python_interview(request):
    _mark_progress(request.user, 'python', 'Python Interview')
    return render(request, 'pythoninterview.html')

def python_comparison(request):
    _mark_progress(request.user, 'python', 'Python Comparison')
    return render(request, 'pythoncomparision.html')

def python_libraries(request):
    _mark_progress(request.user, 'python', 'Python Libraries')
    return render(request, 'pythonlibraries.html')

def py_basics_practice(request):
    test = Test.objects.filter(category="basics").first()

    if request.method == 'POST':
        score = float(request.POST.get('score', 0))

        _save_test_result(
            request.user,
            'python',
            test.name,   # ✅ IMPORTANT
            score
        )

    return render(request, 'pybasicspractice.html', {'test': test})
def py_loop_practice(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == 'POST':
        score = float(request.POST.get('score', 0))

        _save_test_result(
            request.user,
            'python',
            test.name,
            score
        )

    return render(request, 'pylooppractice.html', {'test': test})

def py_function_practice(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    if request.method == 'POST':
        score = float(request.POST.get('score', 0))

        _save_test_result(
            request.user,
            'python',
            test.name,   # ✅ IMPORTANT FIX
            score
        )

    return render(request, "pyfunctionpractice.html", {"test": test})


def python_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    if request.method == 'POST':
        score = float(request.POST.get('score', 0))

        _save_test_result(
            request.user,
            'python',
            test.name,
            score
        )

    return render(request, 'python_test.html', {'test': test})

# ══════════════════════════════════════════════════════════════════
# JAVA MODULE
# ══════════════════════════════════════════════════════════════════

def java_info(request):
    _mark_progress(request.user, 'java', 'Java Info')
    return render(request, 'Java/javainfo.html')

def java_basics(request):
    _mark_progress(request.user, 'java', 'Java Basics')
    return render(request, 'Java/java_basics.html')

def java_control(request):
    _mark_progress(request.user, 'java', 'Java Control Flow')
    return render(request, 'Java/java_control.html')

def java_oop(request):
    _mark_progress(request.user, 'java', 'Java OOP')
    return render(request, 'Java/java_oop.html')

def java_interview(request):
    _mark_progress(request.user, 'java', 'Java Interview')
    return render(request, 'Java/java_interview.html')

def java_vs_python(request):
    return render(request, 'Java/java_vs_languages.html')

def springboot(request):
    return render(request, 'Java/springboot.html')

def java_basic_practice(request):
    test = Test.objects.filter(name="Java Basics Test").first()

    if request.method == 'POST':
        score = float(request.POST.get('score', 0))

        _save_test_result(
            request.user,
            'java',
            test.name,   # ✅ dynamic test name
            score
        )

    return render(request, "java/java_basic_practice.html", {"test": test})

def java_loop_practice(request):
    test = Test.objects.filter(name="Java Loop Test").first()

    if request.method == 'POST':
        score = float(request.POST.get('score', 0))

        _save_test_result(
            request.user,
            'java',
            test.name,
            score
        )

    return render(request, "java/java_loop_practice.html", {"test": test})

def java_oop_practice(request):
    test = Test.objects.filter(name="Java OOP Test").first()

    if request.method == 'POST':
        score = float(request.POST.get('score', 0))

        _save_test_result(
            request.user,
            'java',
            test.name,
            score
        )

    return render(request, "java/java_oop_practice.html", {"test": test})
def java_test(request):
    test = Test.objects.filter(name="Java Test").first()

    if request.method == 'POST':
        score = float(request.POST.get('score', 0))

        _save_test_result(
            request.user,
            'java',
            test.name,
            score
        )

    return render(request, "java/java_test.html", {"test": test})


# ══════════════════════════════════════════════════════════════════
# C++ MODULE
# ══════════════════════════════════════════════════════════════════

def cpp_info(request):
    _mark_progress(request.user, 'cpp', 'C++ Info')
    return render(request, 'cpp/cppinfo.html')

def cpp_basics(request):
    _mark_progress(request.user, 'cpp', 'C++ Basics')
    return render(request, 'cpp/cpp_basics.html')

def cpp_control(request):
    _mark_progress(request.user, 'cpp', 'C++ Control Flow')
    return render(request, 'cpp/cpp_control.html')

def cpp_oop(request):
    _mark_progress(request.user, 'cpp', 'C++ OOP')
    return render(request, 'cpp/cpp_oop.html')

def cpp_practice(request):
    # Get the C++ test object
    test = Test.objects.filter(name="C++ Practice").first()
    
    # Mark practice progress
    _mark_progress(request.user, 'cpp', 'C++ Practice', 'practice')
    
    # Pass test to template
    return render(request, 'cpp/cpp_practice.html', {"test": test})
def cpp_test(request):
    # This will raise a 404 if no test exists
    test = Test.objects.filter(name="C++ Test").first()
    
    if request.method == 'POST':
        score = float(request.POST.get('score', 0))

        _save_test_result(
            request.user,
            'cpp',
            test.name,
            score
        )

    return render(request, "cpp/cpp_test.html", {"test": test})
# ══════════════════════════════════════════════════════════════════
# JAVASCRIPT MODULE
# ══════════════════════════════════════════════════════════════════

def js_info(request):
    _mark_progress(request.user, 'javascript', 'JS Info')
    return render(request, 'js/javasinfo.html')

def js_basics(request):
    _mark_progress(request.user, 'javascript', 'JS Basics')
    return render(request, 'js/js_basics.html')

def js_control(request):
    _mark_progress(request.user, 'javascript', 'JS Control Flow')
    return render(request, 'js/js_control.html')

def js_dom(request):
    _mark_progress(request.user, 'javascript', 'JS DOM')
    return render(request, 'js/js_dom.html')

def js_es6(request):
    _mark_progress(request.user, 'javascript', 'JS ES6+')
    return render(request, 'js/js_es6.html')

def js_practice(request):
    test = Test.objects.filter(name="JavaScript Practice").first()
    _mark_progress(request.user, 'js', 'javascript Practice', 'practice')
    return render(request, 'js/js_practice.html', {"test": test})

def js_test(request):
    test = Test.objects.filter(name="JavaScript Test").first()
    
    if request.method == 'POST':
        score = float(request.POST.get('score', 0))

        _save_test_result(
            request.user,
            'js',
            test.name,
            score
        )

    return render(request, "js/js_test.html", {"test": test})


# ══════════════════════════════════════════════════════════════════
# SQL MODULE
# ══════════════════════════════════════════════════════════════════

def sql_info(request):
    _mark_progress(request.user, 'sql', 'SQL Info')
    return render(request, 'sql/sql_info.html')

def sql_basics(request):
    _mark_progress(request.user, 'sql', 'SQL Basics')
    return render(request, 'sql/sql_basics.html')

def sql_queries(request):
    _mark_progress(request.user, 'sql', 'SQL Queries')
    return render(request, 'sql/sql_queries.html')

def sql_joins(request):
    _mark_progress(request.user, 'sql', 'SQL Joins')
    return render(request, 'sql/sql_joins.html')

def sql_advanced(request):
    _mark_progress(request.user, 'sql', 'Advanced SQL')
    return render(request, 'sql/sql_advanced.html')

def sql_practice(request):
     test = Test.objects.filter(name="SQL Practice").first()
     _mark_progress(request.user, 'sql', 'SQL Practice', 'practice')
     return render(request, 'sql/sql_practice.html', {"test": test})

def sql_test(request):
    test = Test.objects.filter(name="SQL Test").first()

    if request.method == "POST":
        score = int(request.POST.get("score", 0))

        result = _save_test_result(request.user, 'sql', test.name, score)

        return JsonResponse({
            "redirect_url": f"/result/{result.id}/"
        })

    return render(request, "sql/sql_test.html", {"test": test})
# ══════════════════════════════════════════════════════════════════
# DSA MODULE
# ══════════════════════════════════════════════════════════════════

def dsa_info(request):
    _mark_progress(request.user, 'dsa', 'DSA Info')
    return render(request, 'ds/dsa_info.html')

def dsa_basics(request):
    _mark_progress(request.user, 'dsa', 'DSA Basics')
    return render(request, 'ds/dsa_basics.html')

def dsa_linear(request):
    _mark_progress(request.user, 'dsa', 'Linear DS')
    return render(request, 'ds/dsa_linear.html')

def dsa_sort(request):
    _mark_progress(request.user, 'dsa', 'Sorting Algorithms')
    return render(request, 'ds/dsa_sort.html')

def dsa_practice(request):
    test = Test.objects.filter(name="DSA Practice").first()
    _mark_progress(request.user, 'dsa', 'DSA Practice', 'practice')
    return render(request, 'ds/dsa_practice.html', {"test": test})

def dsa_test(request):
     test = Test.objects.filter(name="DSA Test").first()

     if request.method == "POST":
        score = int(request.POST.get("score", 0))

        result = _save_test_result(request.user, 'dsa', test.name, score)

        return JsonResponse({
            "redirect_url": f"/result/{result.id}/"
        })

     return render(request, "ds/dsa_test.html", {"test": test})

# ══════════════════════════════════════════════════════════════════
# COMPANY MODULE
# ══════════════════════════════════════════════════════════════════

def companies_blogs(request):
    return render(request, 'company.html')

def google(request):    return render(request, 'company/google.html')
def amazon(request):    return render(request, 'company/amazon.html')
def microsoft(request): return render(request, 'company/microsoft.html')
def meta(request):      return render(request, 'company/meta.html')

def interview_tips(request):    return render(request, 'blog/interview-tips.html')
def resume_guide(request):      return render(request, 'blog/resume-guide.html')
def tech_trends(request):       return render(request, 'blog/tech-trends.html')
def experience_stories(request):return render(request, 'blog/experience-stories.html')


# ══════════════════════════════════════════════════════════════════
# COMMUNICATION MODULE
# ══════════════════════════════════════════════════════════════════

def time_management(request):
    _mark_progress(request.user, 'communication', 'Time Management')
    return render(request, 'communication/time_management.html')

def teamwork(request):
    _mark_progress(request.user, 'communication', 'Teamwork')
    return render(request, 'communication/teamwork.html')

def interviewskills(request):
    _mark_progress(request.user, 'communication', 'Interview Skills')
    return render(request, 'communication/interviewskills.html')

def personality(request):
    _mark_progress(request.user, 'communication', 'Personality Development')
    return render(request, 'communication/personality.html')

def verbal(request):
    _mark_progress(request.user, 'communication', 'Verbal Communication')
    return render(request, 'communication/verbal.html')

def non_verbal(request):
    _mark_progress(request.user, 'communication', 'Non-Verbal Communication')
    return render(request, 'communication/non_verbal.html')

def listening(request):
    _mark_progress(request.user, 'communication', 'Listening Skills')
    return render(request, 'communication/listening.html')

def comm_quiz(request):
    if request.method == 'POST':
        try:
            score = float(request.POST.get('score', 0))
            _save_test_result(request.user, 'communication', 'Communication Quiz', score)
        except (ValueError, TypeError):
            pass
    return render(request, 'communication/comm_quiz.html')


# ══════════════════════════════════════════════════════════════════
# APTITUDE MODULE
# ══════════════════════════════════════════════════════════════════

def is_subscribed(user):
    if not user.is_authenticated:
        return False
    try:
        return user.subscription.is_premium
    except Exception:
        return False

def practice_hub(request):
    return render(request, 'questions.html', {'subscribed': is_subscribed(request.user)})

def aptitude_practice(request):
    _mark_progress(request.user, 'aptitude', 'Aptitude Practice', 'practice')
    return render(request, 'aptitude/aptitude_practice.html')

def aptitude_test(request):
    if request.method == 'POST':
        try:
            score = float(request.POST.get('score', 0))
            _save_test_result(request.user, 'aptitude', 'Aptitude Test', score)
        except (ValueError, TypeError):
            pass
    return render(request, 'aptitude/aptitude_test.html')

def technical_practice(request):
    _mark_progress(request.user, 'aptitude', 'Technical Practice', 'practice')
    return render(request, 'aptitude/technical_practice.html')

def technical_test(request):
    if request.method == 'POST':
        try:
            score = float(request.POST.get('score', 0))
            _save_test_result(request.user, 'aptitude', 'Technical Test', score)
        except (ValueError, TypeError):
            pass
    return render(request, 'aptitude/technical_test.html')

def interview_practice(request):
    _mark_progress(request.user, 'aptitude', 'Interview Practice', 'practice')
    return render(request, 'aptitude/interview_practice.html')

def interview_test(request):
    if request.method == 'POST':
        try:
            score = float(request.POST.get('score', 0))
            _save_test_result(request.user, 'aptitude', 'Interview Test', score)
        except (ValueError, TypeError):
            pass
    return render(request, 'aptitude/interview_test.html')


# ══════════════════════════════════════════════════════════════════
# PREMIUM DASHBOARD
# ══════════════════════════════════════════════════════════════════

def premium_dashboard(request):
    from .models import TestResult, UserProgress
    sub = _get_subscription(request.user)

    if request.user.is_authenticated:
        recent_results = TestResult.objects.filter(
            user=request.user).order_by('-date_attempted')[:5]
        progress = UserProgress.objects.filter(
            user=request.user, completed=True).count()
        total_topics = UserProgress.objects.filter(
            user=request.user).count()
    else:
        recent_results = []
        progress = total_topics = 0

    return render(request, 'premium_dashboard.html', {
        'subscribed':     sub.is_premium if sub else False,
        'recent_results': recent_results,
        'completed':      progress,
        'total_topics':   total_topics,
    })
    
    #plans
@login_required
def plans(request):
    return render(request, 'plans.html')


# 🟢 Login Page
def login_view(request):
    return render(request, 'login.html')


@login_required
def start_trial(request):
    from datetime import timedelta
    from django.utils import timezone
    from .models import Subscription

    Subscription.objects.update_or_create(
        user=request.user,
        defaults={
            'plan': 'premium',
            'status': 'active',
            'expires_at': timezone.now() + timedelta(days=7)
        }
    )

    return redirect('index')

@login_required
def submit_test(request, test_id):
    print("VIEW HIT")

    if request.method == "POST":

        test = get_object_or_404(Test, id=test_id)

        total = int(request.POST.get("total") or 0)
        correct = int(request.POST.get("correct") or 0)
        wrong = int(request.POST.get("wrong") or 0)
        skipped = int(request.POST.get("skipped") or 0)
        score = int(request.POST.get("score") or 0)
        time_taken = int(request.POST.get("time_taken") or 0)

        # Get descriptive answers
        desc1 = request.POST.get("desc1", "")
        desc2 = request.POST.get("desc2", "")
        desc3 = request.POST.get("desc3", "")
        desc4 = request.POST.get("desc4", "")
        desc5 = request.POST.get("desc5", "")

        result = TestResult.objects.create(
            user=request.user,
            test=test,
            total_questions=total,
            correct_answers=correct,
            wrong_answers=wrong,
            skipped_questions=skipped,
            marks=score,
            time_taken=time_taken,
            desc1=desc1,
            desc2=desc2,
            desc3=desc3,
            desc4=desc4,
            desc5=desc5
        )

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"redirect_url": reverse('result', args=[result.id])})
        
        # If normal POST, just redirect
        return redirect('result', result_id=result.id)
def result_page(request, result_id):
    result = get_object_or_404(TestResult, id=result_id)
    return render(request, 'result.html', {'result': result})


import json
import uuid
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
# ──────────────────────────────────────────────
# 1.  PLANS PAGE  (no changes needed, already works)
# ──────────────────────────────────────────────
def plans(request):
    return render(request, 'plans.html')
 
 
# ──────────────────────────────────────────────
# 2.  PAYMENT PAGE  (replaces the old 1-liner)
# ──────────────────────────────────────────────
def payment(request):
    # Optional: redirect to login if not authenticated
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'payment.html')
 
 
# ──────────────────────────────────────────────
# 3.  PAYMENT VERIFY  (new endpoint — called by JS)
# ──────────────────────────────────────────────
@login_required
def payment_verify(request):
    """
    Called via fetch() from payment.html after the dummy Razorpay
    animation completes.  Marks the user's subscription as Premium
    and saves a PaymentRecord.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
 
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
 
    txn_id = data.get('razorpay_payment_id', f"DEMO_{uuid.uuid4().hex[:12].upper()}")
    plan   = data.get('plan', 'premium')
    amount = data.get('amount', 299)
 
    # ── Save / update Subscription ──────────────────────────────
    from .models import Subscription, PaymentRecord
 
    sub, _ = Subscription.objects.get_or_create(user=request.user)
    sub.plan       = plan
    sub.status     = 'active'
    sub.expires_at = timezone.now() + timedelta(days=30)
    sub.save()
 
    # ── Save PaymentRecord ───────────────────────────────────────
    PaymentRecord.objects.create(
        user           = request.user,
        plan           = plan,
        amount         = amount,
        currency       = 'INR',
        status         = 'success',
        method         = 'other',          # dummy — no real method known
        transaction_id = txn_id,
        notes          = 'Demo Razorpay payment (academic project)',
    )
 
    return JsonResponse({
        'status'         : 'success',
        'transaction_id' : txn_id,
        'plan'           : plan,
        'expires_at'     : sub.expires_at.isoformat(),
    })