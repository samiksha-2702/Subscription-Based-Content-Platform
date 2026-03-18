from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib import messages
from django.utils import timezone


# ══════════════════════════════════════════════════════════════════
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



def _record_login(request, user):
    """Record every successful login to LoginHistory."""
    try:
        from .models import LoginHistory
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')
        ua = request.META.get('HTTP_USER_AGENT', '')[:500]
        LoginHistory.objects.create(user=user, ip_address=ip, user_agent=ua)
    except Exception:
        pass  # never let this break the login flow

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
    """Save a TestResult row and also feed the AI tracker."""
    if not user.is_authenticated:
        return
    from .models import TestResult
    TestResult.objects.create(
        user=user, module=module, test_name=test_name,
        score=score_pct, total_questions=total_q,
        correct_answers=correct, time_taken=time_sec,
    )
    # Also record for AI recommendations engine
    SLUG_MAP = {
        'python':       'python-basics',
        'java':         'java-basics',
        'cpp':          'cpp-basics',
        'javascript':   'js-basics',
        'sql':          'sql-basics',
        'dsa':          'dsa-basics',
        'communication':'comm-interview',
        'aptitude':     'comm-interview',
    }
    slug = SLUG_MAP.get(module)
    if slug:
        try:
            from ai_recommendations.views import record_quiz_attempt
            record_quiz_attempt(user, slug, score_pct)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════
# AUTH VIEWS
# ══════════════════════════════════════════════════════════════════

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    error = None
    username = ''
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            _ensure_profile(user)
            _get_subscription(user)
            _record_login(request, user)
            next_url = request.GET.get('next') or request.POST.get('next') or 'index'
            return redirect(next_url)
        else:
            error = 'Invalid username or password. Please try again.'
    return render(request, 'login.html', {'error': error, 'username': username})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    error = None
    username = email = full_name = ''
    if request.method == 'POST':
        username  = request.POST.get('username',  '').strip()
        full_name = request.POST.get('full_name', '').strip()
        email     = request.POST.get('email',     '').strip()
        password  = request.POST.get('password',  '')
        password2 = request.POST.get('password2', '')
        if not username:
            error = 'Username is required.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters.'
        elif password != password2:
            error = 'Passwords do not match.'
        elif User.objects.filter(username=username).exists():
            error = f'Username "{username}" is already taken.'
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            if full_name:
                parts = full_name.split(' ', 1)
                user.first_name = parts[0]
                user.last_name  = parts[1] if len(parts) > 1 else ''
                user.save()
            _ensure_profile(user)
            _get_subscription(user)   # creates free subscription
            login(request, user)
            return redirect('index')
    return render(request, 'register.html', {
        'error': error, 'username': username,
        'email': email, 'full_name': full_name,
    })


def logout_view(request):
    logout(request)
    return redirect('index')


# ══════════════════════════════════════════════════════════════════
# MAIN PAGES
# ══════════════════════════════════════════════════════════════════

def index(request):
    return render(request, 'index.html')

def programming(request):
    return render(request, 'programming.html')

def company(request):
    return render(request, 'company.html')

def expert_talks(request):
    return render(request, 'expert/expert.html')

def communication(request):
    return render(request, 'communication/comm.html')

def aptitude(request):
    sub = _get_subscription(request.user)
    return render(request, 'questions.html', {
        'subscribed': sub.is_premium if sub else False
    })

def ai_recommendation(request):
    return render(request, 'ai.html')

def plans(request):
    return render(request, 'plans.html')

def subscribe(request):
    return render(request, 'plans.html')

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
    _mark_progress(request.user, 'python', 'Basics Practice', 'practice')
    return render(request, 'pybasicspractice.html')

def py_loop_practice(request):
    _mark_progress(request.user, 'python', 'Loop Practice', 'practice')
    return render(request, 'pylooppractice.html')

def py_function_practice(request):
    _mark_progress(request.user, 'python', 'Function Practice', 'practice')
    return render(request, 'pyfunctionpractice.html')

@ensure_csrf_cookie
def python_test(request):
    if request.method == 'POST':
        try:
            score = float(request.POST.get('score', 0))
            _save_test_result(request.user, 'python', 'Python Test', score)
            _mark_progress(request.user, 'python', 'Python Test', 'test', completed=True)
        except (ValueError, TypeError):
            pass
    return render(request, 'python_test.html')


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
    _mark_progress(request.user, 'java', 'Java Basics Practice', 'practice')
    return render(request, 'Java/java_basic_practice.html')

def java_loop_practice(request):
    _mark_progress(request.user, 'java', 'Java Loop Practice', 'practice')
    return render(request, 'Java/java_loop_practice.html')

def java_oop_practice(request):
    _mark_progress(request.user, 'java', 'Java OOP Practice', 'practice')
    return render(request, 'Java/java_oop_practice.html')

@ensure_csrf_cookie
def java_test(request):
    if request.method == 'POST':
        try:
            score = float(request.POST.get('score', 0))
            _save_test_result(request.user, 'java', 'Java Test', score)
            _mark_progress(request.user, 'java', 'Java Test', 'test', completed=True)
        except (ValueError, TypeError):
            pass
    return render(request, 'Java/java_test.html')


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
    _mark_progress(request.user, 'cpp', 'C++ Practice', 'practice')
    return render(request, 'cpp/cpp_practice.html')

@ensure_csrf_cookie
def cpp_test(request):
    if request.method == 'POST':
        try:
            score = float(request.POST.get('score', 0))
            _save_test_result(request.user, 'cpp', 'C++ Test', score)
            _mark_progress(request.user, 'cpp', 'C++ Test', 'test', completed=True)
        except (ValueError, TypeError):
            pass
    return render(request, 'cpp/cpp_test.html')


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
    _mark_progress(request.user, 'javascript', 'JS Practice', 'practice')
    return render(request, 'js/js_practice.html')

@ensure_csrf_cookie
def js_test(request):
    if request.method == 'POST':
        try:
            score = float(request.POST.get('score', 0))
            _save_test_result(request.user, 'javascript', 'JS Test', score)
            _mark_progress(request.user, 'javascript', 'JS Test', 'test', completed=True)
        except (ValueError, TypeError):
            pass
    return render(request, 'js/js_test.html')


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
    _mark_progress(request.user, 'sql', 'SQL Practice', 'practice')
    return render(request, 'sql/sql_practice.html')

@ensure_csrf_cookie
def sql_test(request):
    if request.method == 'POST':
        try:
            score = float(request.POST.get('score', 0))
            _save_test_result(request.user, 'sql', 'SQL Test', score)
            _mark_progress(request.user, 'sql', 'SQL Test', 'test', completed=True)
        except (ValueError, TypeError):
            pass
    return render(request, 'sql/sql_test.html')


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
    _mark_progress(request.user, 'dsa', 'DSA Practice', 'practice')
    return render(request, 'ds/dsa_practice.html')

@ensure_csrf_cookie
def dsa_test(request):
    if request.method == 'POST':
        try:
            score = float(request.POST.get('score', 0))
            _save_test_result(request.user, 'dsa', 'DSA Test', score)
            _mark_progress(request.user, 'dsa', 'DSA Test', 'test', completed=True)
        except (ValueError, TypeError):
            pass
    return render(request, 'ds/dsa_test.html')


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
            user=request.user).order_by('-attempted_at')[:5]
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


# ══════════════════════════════════════════════════════════════════
# PAYMENT VIEW
# Called when user clicks "Pay Now" on payment.html
# Records a PaymentRecord and upgrades subscription on success
# ══════════════════════════════════════════════════════════════════

@require_POST
def process_payment(request):
    """
    Receives payment form data, records a PaymentRecord,
    and upgrades the user's subscription to Premium.
    In production replace this with a real payment gateway.
    """
    from .models import PaymentRecord, Subscription
    import json

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'msg': 'Login required'}, status=401)

    # Accept both JSON and regular form POST
    try:
        if request.content_type and 'json' in request.content_type:
            data   = json.loads(request.body)
            amount = float(data.get('amount', 499))
            method = data.get('method', 'card')
            txn_id = data.get('transaction_id', '')
        else:
            amount = float(request.POST.get('amount', 499))
            method = request.POST.get('method', 'card')
            txn_id = request.POST.get('transaction_id', '')
    except (ValueError, Exception):
        amount, method, txn_id = 499, 'card', ''

    # Record payment
    payment = PaymentRecord.objects.create(
        user           = request.user,
        plan           = 'premium',
        amount         = amount,
        currency       = 'INR',
        method         = method,
        transaction_id = txn_id,
        status         = 'success',   # mark success directly (replace with gateway check)
        notes          = 'Self-serve payment via PrepEdge plans page',
    )

    # Upgrade subscription
    from datetime import timedelta
    Subscription.objects.update_or_create(
        user=request.user,
        defaults={
            'plan':       'premium',
            'status':     'active',
            'expires_at': timezone.now() + timedelta(days=30),
        }
    )

    if request.content_type and 'json' in request.content_type:
        return JsonResponse({'status': 'ok', 'payment_id': payment.id})

    from django.contrib import messages
    messages.success(request, '🎉 Payment successful! You are now a Premium member.')
    return redirect('index')
    
    #plans
def plans(request):
    return render(request, 'plans.html')


# 🟢 Login Page
def login_view(request):
    return render(request, 'login.html')


# 🟢 Payment Page
def payment(request):
    return render(request, 'payment.html')
