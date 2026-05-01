from re import sub

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
from django.http import HttpResponse
from .models import Subscription, PaymentRecord
from django.conf import settings
import razorpay
from django.contrib.auth import update_session_auth_hash
from functools import wraps
# views.py

PLANS = {
    "monthly": {
        "price": 299,
        "days": 30
    },
    "yearly": {
        "price": 999,
        "days": 365
    }
}

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
            print("LOGIN SUCCESS")
            login(request, user)

            # ✅ CHECK SUBSCRIPTION
            subscription = get_active_subscription(user)

            if has_active_subscription(user):
              return redirect("index")
            else:
              return redirect("plans")
        else:
            return render(request, "login.html", {
                "error": "Invalid username or password",
                "username": username
            })

    return render(request, "login.html")

from django.utils import timezone

def has_active_subscription(user):
    if not user.is_authenticated:
        return False

    sub = Subscription.objects.filter(user=user).first()

    if not sub:
        return False

    # expire check
    if sub.expires_at and sub.expires_at < timezone.now():
        sub.status = 'expired'
        sub.save()
        return False

    # ✅ FIXED LOGIC
    return sub.status == 'active' and sub.plan in ['monthly', 'yearly', 'premium']

@login_required
def user_logout(request):
    logout(request)
    return redirect('login')

from functools import wraps

def premium_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        sub = Subscription.objects.filter(user=request.user).first()
        # print("DEBUG SUB:", sub.plan if sub else None, sub.status if sub else None)

        if not has_active_subscription(request.user):
            return redirect('plans')
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
def profile_view(request):
    user = request.user

    # USER RESULTS
    results = TestResult.objects.filter(user=user).order_by('-date_attempted')

    total_tests = results.count()
    avg_score = results.aggregate(avg=Avg('score'))['avg'] or 0
    last_result = results.first()

    # SUBSCRIPTION
    subscription = get_active_subscription(user)

    # 📊 CHART DATA (last 10 tests)
    recent_results = results[:10][::-1]

    chart_labels = json.dumps([
    r.test.name if r.test else "Test"
    for r in recent_results
])

    chart_scores = json.dumps([
    float(r.score) for r in recent_results
])

    # 🏆 LEADERBOARD (Top 5 users)
    leaderboard = (
        TestResult.objects
        .values('user__id', 'user__username')
        .annotate(avg_score=Avg('score'))
        .order_by('-avg_score')[:5]
    )

    # 🏆 USER RANK
    all_users = list(
        TestResult.objects
        .values('user__id')
        .annotate(avg_score=Avg('score'))
        .order_by('-avg_score')
    )

    rank_position = None
    for i, u in enumerate(all_users):
        if u['user__id'] == user.id:
            rank_position = i + 1
            break

    # CONTEXT
    context = {
        'results': results,
        'total_tests': total_tests,
        'avg_score': round(avg_score, 2),
        'last_active': last_result.date_attempted if last_result else None,

        # subscription
        'subscription': subscription,
        'is_premium': has_active_subscription(user),

        # chart
        'chart_labels': chart_labels,
        'chart_scores': chart_scores,

        # leaderboard
        'leaderboard': leaderboard,
        'rank_position': rank_position,
    }

    return render(request, 'profile.html', context)

from ai_recommendations.models import UserQuizAttempt
from ai_recommendations.views import _refresh_weak_areas, _generate_recommendations

def delete_test_result(request, id):
    result = TestResult.objects.get(id=id)

    UserQuizAttempt.objects.filter(
        user=request.user,
        topic__name=result.test.name
    ).delete()

    result.delete()

    # 🔥 refresh AI
    _refresh_weak_areas(request.user)
    _generate_recommendations(request.user)

    return redirect('profile')

def activate_subscription(user):
    subscription, created = Subscription.objects.get_or_create(user=user)

    subscription.plan = 'premium'
    subscription.status = 'active'
    subscription.expires_at = timezone.now() + timedelta(days=30)

    subscription.save()
    return subscription

@login_required
def activate_free(request):
    activate_free_plan(request.user)
    return redirect('profile')

def activate_free_plan(user):
    subscription, created = Subscription.objects.get_or_create(user=user)

    subscription.plan = 'free'
    subscription.status = 'active'
    subscription.expires_at = None   # unlimited free  # free = no expiry

    subscription.save()
    return subscription
    

def check_expiry(user):
    subscription = getattr(user, 'subscription', None)

    if subscription and subscription.expires_at:
        if subscription.expires_at < timezone.now():
            subscription.status = 'expired'
            subscription.save()
            
from django.utils import timezone

def get_active_subscription(user):
    if not user.is_authenticated:
        return None

    sub = Subscription.objects.filter(user=user).first()

    if not sub:
        return None

    # auto-expire
    if sub.expires_at and sub.expires_at < timezone.now():
        sub.status = 'expired'
        sub.save()

    return sub

@login_required
def plans(request):
    subscription = get_active_subscription(request.user)

    return render(request, "plans.html", {
        "subscription": subscription,
        "is_premium": subscription.is_premium if subscription else False
    })
    
@login_required
def upgrade_view(request):
    subscription = get_active_subscription(request.user)

    if has_active_subscription(request.user):
        # ✅ Show message instead of redirect confusion
        return redirect("plans")  

    return render(request, "plans.html")

@login_required
def cancel_subscription(request):
    sub = Subscription.objects.filter(user=request.user).first()

    if sub:
        sub.plan = 'free'
        sub.status = 'cancelled'
        sub.expires_at = None
        sub.save()

    return redirect('profile')

from .models import Feedback
@login_required
def about(request):
    if request.method == "POST":
        Feedback.objects.create(
            name=request.POST.get("name"),
            email=request.POST.get("email"),
            message=request.POST.get("message")
        )

        messages.success(request, "Message saved successfully!")

    return render(request, 'about.html')

@login_required
def edit_profile(request):

    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone")

        if not username or not email:
            messages.error(request, "Username and Email are required")
        else:
            user.username = username
            user.email = email
            user.save()

           
            profile.phone = phone
            profile.save()

            messages.success(request, "Profile updated successfully")
            return redirect("profile")

    return render(request, "edit_profile.html", {
        "user": user,
        "profile": profile
    })


# 🔐 CHANGE PASSWORD
@login_required
def change_password(request):
    if request.method == "POST":
        current = request.POST.get('current_password')
        new = request.POST.get('new_password')
        confirm = request.POST.get('confirm_password')

        user = request.user

        if not user.check_password(current):
            messages.error(request, "Current password is wrong")
            return redirect('change_password')

        if new != confirm:
            messages.error(request, "Passwords do not match")
            return redirect('change_password')

        user.set_password(new)
        user.save()

        messages.success(request, "Password updated successfully")
        return redirect('login')

    return render(request, 'change_password.html')
# HELPERS
# ══════════════════════════════════════════════════════════════════
def is_subscribed(user):
    sub = Subscription.objects.filter(user=user).first()
    return sub.is_premium if sub else False

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
    """
    Save a TestResult and notify the AI recommendations engine.
    
    BUG FIXED: was using `marks=` which doesn't exist on TestResult.
               Corrected to `score=` and `obtained_marks=`.
    """
    if not user.is_authenticated:
        return None
 
    from .models import TestResult, Test
 
    test = Test.objects.filter(name=test_name).first()
 
    # Recalculate score from correct/total if provided
    if total_q > 0 and correct > 0:
        score_pct = round((correct / total_q) * 100, 2)
 
    result = TestResult.objects.create(
        user             = user,
        test             = test,
        total_questions  = total_q,
        correct_answers  = correct,
        score            = score_pct,       # ✅ FIXED: was `marks=`
        obtained_marks   = correct,
        time_taken       = time_sec,
    )
 
    # ── Notify AI recommendations engine ─────────────────────────────────
    # Maps module keys used in app1 → module keys understood by ai_recommendations
    MODULE_MAP = {
        'python':   'python',
        'java':     'java',
        'cpp':      'cpp',
        'js':       'javascript',
        'sql':      'sql',
        'dsa':      'dsa',
        'comm':     'communication',
        'apti':     'aptitude',
        'tech':     'tech',
        'interv':   'interv',
    }
    ai_module = MODULE_MAP.get(module, module)
 
    try:
        from ai_recommendations.views import record_quiz_attempt
        record_quiz_attempt(user, ai_module, score_pct, topic_name=test_name)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("AI rec update failed: %s", exc)
 
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
@premium_required
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
@premium_required
def ai_recommendation(request):
  return render(request, 'ai/dashboard.html')

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

@premium_required
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
@premium_required
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
    _mark_progress(request.user, 'cpp', 'Cpp Basics')
    return render(request, 'cpp/cpp_basics.html')

def cpp_control(request):
    _mark_progress(request.user, 'cpp', 'C++ Control Flow')
    return render(request, 'cpp/cpp_control.html')

def cpp_oop(request):
    _mark_progress(request.user, 'cpp', 'C++ OOP')
    return render(request, 'cpp/cpp_oop.html')

def cpp_practice(request, test_id):
    test = Test.objects.filter(name="C++ Practice").first()

    if request.method == "POST":
        score = float(request.POST.get("score", 0))

        TestResult.objects.create(
            request.user,
            'cpp',
            test.name,
            score=score
        )

    return render(request, "cpp/cpp_practice.html", {"test": test})

@premium_required
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
@premium_required
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
@premium_required
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
@premium_required
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
@premium_required
def google(request):  
    return render(request, 'company/google.html')
@premium_required
def amazon(request):  
    return render(request, 'company/amazon.html')
@premium_required
def microsoft(request):
    return render(request, 'company/microsoft.html')
@premium_required
def meta(request):   
    return render(request, 'company/meta.html')

def interview_tips(request):  
    return render(request, 'blog/interview-tips.html')
def resume_guide(request):   
    return render(request, 'blog/resume-guide.html')
@premium_required
def tech_trends(request):  
    return render(request, 'blog/tech-trends.html')
@premium_required
def experience_stories(request):
    return render(request, 'blog/experience-stories.html')


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
@premium_required
def comm_quiz(request):
    test = Test.objects.filter(name="communication Test").first()
    return render(request, 'communication/comm_quiz.html', {"test": test})


# ══════════════════════════════════════════════════════════════════
# APTITUDE MODULE
# ══════════════════════════════════════════════════════════════════


def practice_hub(request):
    return render(request, 'questions.html', {'subscribed':  has_active_subscription(request.user)})

def aptitude_practice(request):
    test = Test.objects.filter(name="Aptitude Practice Test").first()
    _mark_progress(request.user, 'apti', 'Aptitude Practice Test', 'practice')
    return render(request, 'aptitude/aptitude_practice.html', {"test": test})

def aptitude_test(request):
    test = Test.objects.filter(name="Aptitude Test").first()

    if request.method == "POST":
        score = int(request.POST.get("score", 0))

        result = _save_test_result(request.user, 'apti', test.name, score)

        return JsonResponse({
            "redirect_url": f"/result/{result.id}/"
        })

    return render(request, "aptitude/aptitude_test.html", {"test": test})

def technical_practice(request):
    if not has_active_subscription(request.user):
        return redirect('plans')   # 🔒 BLOCK FREE USERS

    test = Test.objects.filter(name="Technical Practice Test").first()

    if not test:
        return render(request, 'aptitude/technical_practice.html', {
            "error": "Test not found"
        })

    _mark_progress(request.user, 'tech', 'Technical Practice Test', 'practice')

    return render(request, 'aptitude/technical_practice.html', {
        "test": test
    })
 
def technical_test(request):
    if not has_active_subscription(request.user):
        return redirect('plans')

    test = Test.objects.filter(name="Technical Test").first()

    if request.method == "POST":
        score = int(request.POST.get("score", 0))
        result = _save_test_result(request.user, 'tech', test.name, score)

        return JsonResponse({
            "redirect_url": f"/result/{result.id}/"
        })

    return render(request, "aptitude/technical_test.html", {"test": test})

def interview_practice(request):
    if not has_active_subscription(request.user):
        return redirect('plans')

    test = Test.objects.filter(name="Interview Practice Test").first()

    if not test:
        return HttpResponse("Test not found.")

    _mark_progress(request.user, 'interv', 'Interview Practice Test', 'practice')

    return render(request, 'aptitude/interview_practice.html', {
        "test": test
    })
def interview_test(request):
    if not has_active_subscription(request.user):
        return redirect('plans')

    test = Test.objects.filter(name="Interview Test").first()

    if request.method == "POST":
        score = int(request.POST.get("score", 0))
        result = _save_test_result(request.user, 'interv', test.name, score)

        return JsonResponse({
            "redirect_url": f"/result/{result.id}/"
        })

    return render(request, "aptitude/interview_test.html", {"test": test})
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
    if request.method != "POST":
        return redirect('index')
 
    test = get_object_or_404(Test, id=test_id)
 
    total      = int(request.POST.get("total") or 0)
    correct    = int(request.POST.get("correct") or 0)
    wrong      = int(request.POST.get("wrong") or 0)
    skipped    = int(request.POST.get("skipped") or 0)
    time_taken = int(request.POST.get("time_taken") or 0)
 
    score = round((correct / test.total_marks) * 100, 2) if test.total_marks > 0 else 0
 
    result = TestResult.objects.create(
        user              = request.user,
        test              = test,
        total_questions   = total,
        correct_answers   = correct,
        wrong_answers     = wrong,
        skipped_questions = skipped,
        score             = score,
        obtained_marks    = correct,
        time_taken        = time_taken,
        desc1             = request.POST.get("desc1", ""),
        desc2             = request.POST.get("desc2", ""),
        desc3             = request.POST.get("desc3", ""),
        desc4             = request.POST.get("desc4", ""),
        desc5             = request.POST.get("desc5", ""),
    )
 
    # ── Notify AI recommendations engine ─────────────────────────────────
    # Map test.language to the module key used in ai_recommendations
    LANG_TO_MODULE = {
        'python': 'python',
        'java':   'java',
        'cpp':    'cpp',
        'js':     'javascript',
        'sql':    'sql',
        'dsa':    'dsa',
        'comm':   'communication',
        'apti':   'aptitude',
        'tech':   'tech',
        'interv': 'interv',
    }
    ai_module = LANG_TO_MODULE.get(test.language, test.language)
 
    try:
        from ai_recommendations.views import record_quiz_attempt
        record_quiz_attempt(request.user, ai_module, score, topic_name=test.name)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("AI rec update failed in submit_test: %s", exc)
 
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"redirect_url": reverse('result', args=[result.id])})
 
    return redirect('result', result.id)
  
def result_page(request, result_id):
    result = get_object_or_404(TestResult, id=result_id)
    return render(request, 'result.html', {'result': result})


import json
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect

 
# ──────────────────────────────────────────────
# 2.  PAYMENT PAGE  (replaces the old 1-liner)
# ──────────────────────────────────────────────
import uuid
@login_required
def payment(request):
    return render(request, 'payment.html', {
    'RAZORPAY_KEY_ID': settings.RAZORPAY_KEY_ID
})
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def payment_verify(request):
    try:
        data = json.loads(request.body)
        print("🔥 VERIFY CALLED:", data)

        txn_id = data.get('razorpay_payment_id')
        order_id = data.get('razorpay_order_id')
        signature = data.get('razorpay_signature')
        plan = data.get('plan')

        if not plan:
            return JsonResponse({'error': 'Plan missing'}, status=400)

        client = razorpay.Client(auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        ))

        client.utility.verify_payment_signature({
            'razorpay_payment_id': txn_id,
            'razorpay_order_id': order_id,
            'razorpay_signature': signature
        })

        plan_data = PLANS[plan]
        duration = plan_data["days"]

        sub, _ = Subscription.objects.get_or_create(user=request.user)

        sub.plan = 'premium'
        # sub.plan_type = plan   # add new field if possible
        sub.status = 'active'
        sub.expires_at = timezone.now() + timedelta(days=duration)
        sub.save()

        print("✅ UPDATED:", sub.plan)

        return JsonResponse({'status': 'success'})

    except Exception as e:
        print("❌ ERROR:", str(e))
        return JsonResponse({'status': 'error'})    
@login_required
def create_order(request):
    try:
        data = json.loads(request.body)
        plan = data.get("plan")

        if plan not in PLANS:
            return JsonResponse({"error": "Invalid plan"}, status=400)

        amount = PLANS[plan]["price"] * 100  # in paise

        client = razorpay.Client(auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        ))

        order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": "1"
        })

        print("🟢 ORDER CREATED:", order["id"])
        return JsonResponse(order)

    except Exception as e:
        print("❌ CREATE ORDER ERROR:", str(e))
        return JsonResponse({"error": "Server error"})