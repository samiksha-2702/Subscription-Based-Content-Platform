"""
ai_recommendations/views.py
────────────────────────────────────────────────────────────────────────────
Fully functional AI Recommendations module for PrepEdge.

HOW IT WORKS
------------
1. record_quiz_attempt()   ← called by app1/views.py after every test
   • Writes a UserQuizAttempt row
   • Calls _refresh_weak_areas() to recompute weakness scores
   • Calls _generate_recommendations() to rebuild recommendation list

2. ai_dashboard()          ← main page the student sees
   • Reads UserWeakArea + UserRecommendation for this user
   • Falls back gracefully when the user has no test history yet

3. refresh_recommendations() ← manual "Refresh" button (POST)
4. dismiss_recommendation()  ← dismiss a card (POST)
5. weak_areas_detail()       ← /ai/weak-areas/
6. learning_path()           ← /ai/learning-path/
7. recommendations_api()     ← JSON widget endpoint
8. record_score()            ← AJAX POST from test pages (alternative entry)
────────────────────────────────────────────────────────────────────────────
"""

import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Avg, Count, Min, Max
from django.utils import timezone
from .models import UserWeakArea
from django.db import transaction


from .models import (
    Topic,
    UserQuizAttempt,
    UserWeakArea,
    UserRecommendation,
    UserPracticeCompletion,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

# Maps the module string used by app1 → Topic slug prefix used in ai_recommendations
MODULE_TO_SLUG = {
    'python':        'python-basics',
    'java':          'java-basics',
    'cpp':           'cpp-basics',
    'javascript':    'js-basics',
    'js':            'js-basics',
    'sql':           'sql-basics',
    'dsa':           'dsa-basics',
    'communication': 'comm-basics',
    'comm':          'comm-basics',
    'aptitude':      'aptitude-basics',
    'apti':          'aptitude-basics',
    'tech':          'technical-basics',
    'interv':        'interview-basics',
}

# Human-readable display names for each module
MODULE_DISPLAY = {
    'python':        'Python',
    'java':          'Java',
    'cpp':           'C++',
    'javascript':    'JavaScript',
    'js':            'JavaScript',
    'sql':           'SQL / Databases',
    'dsa':           'Data Structures & Algorithms',
    'communication': 'Communication',
    'comm':          'Communication',
    'aptitude':      'Aptitude',
    'apti':          'Aptitude',
    'tech':          'Technical',
    'interv':        'Interview Skills',
}

# Score thresholds
WEAK_THRESHOLD   = 20  # below this → weak area
STRONG_THRESHOLD = 80   # above this → strength

def _get_or_create_topic(module: str, topic_name: str = None) -> Topic | None:
    """
    Return the Topic object for a given module slug.
    Creates a placeholder Topic automatically if one doesn't exist yet,
    so the system works even before the admin seeds the Topic table.
    """
    slug = MODULE_TO_SLUG.get(module, f"{module}-basics")
    name = topic_name or MODULE_DISPLAY.get(module, module.title())

    topic, _ = Topic.objects.get_or_create(
        slug=slug,
        defaults={
            'name':       name,
            'module':     module if module in dict(Topic.MODULE_CHOICES) else 'python',
            'difficulty': 'beginner',
        }
    )
    return topic


def _refresh_weak_areas(user):

    attempts = (
        UserQuizAttempt.objects
        .filter(user=user)
        .values('topic')
        .annotate(avg_score=Avg('score'))
    )

    with transaction.atomic():

        # reset
        UserWeakArea.objects.filter(user=user).delete()

        for row in attempts:
            topic_id = row['topic']
            avg_score = row['avg_score'] or 0

            # ✅ ONLY weak areas stored
            if avg_score <= 20:
                UserWeakArea.objects.create(
                    user=user,
                    topic_id=topic_id,
                    reason=f"Weak performance ({avg_score:.1f}%) — needs revision",
                )
    # ❗ No need to manually delete old topics — handled by full reset
    
def _generate_recommendations(user) -> None:
    """
    Rebuild UserRecommendation rows for a user based on their weak areas.

    Strategy
    ────────
    1. Delete old (non-dismissed) recommendations so the list stays fresh.
    2. For each weak area (weakness_score > 0.4) generate:
        a. A 'topic' recommendation → revisit that topic
        b. An 'exercise' recommendation if score < 50%
    3. Add a 'tip' recommendation with general advice.
    4. If the user has NO attempts at all, add a friendly 'get started' tip.
    """
    # Remove stale undismissed recs
    UserRecommendation.objects.filter(user=user, is_dismissed=False).delete()

    weak_areas = [
    {
        'topic': wa.topic.name,
        'module': wa.topic.module,
        'reason': wa.reason
    }
    for wa in UserWeakArea.objects.filter(user=user).select_related('topic')
]

    priority = 1

    for wa in weak_areas:
        topic = wa.topic

        UserRecommendation.objects.create(
            user=user,
            topic=topic,
            rec_type='topic',
            title=f"Revise {topic.name}",
            description=f"{wa.reason}. Focus on core concepts.",
            url=topic.resource_url or f"/{topic.module}/",
            priority=priority,
        )
        priority += 1

        # extra practice for very weak
        if "Weak performance" in wa.reason:
            UserRecommendation.objects.create(
                user=user,
                topic=topic,
                rec_type='exercise',
                title=f"Practice {topic.name}",
                description="Practice questions to improve accuracy.",
                url=f"/{topic.module}/practice/",
                priority=priority,
            )
            priority += 1
    # ── Global tip ────────────────────────────────────────────────────────
    total_attempts = UserQuizAttempt.objects.filter(user=user).count()

    if total_attempts == 0:
        tip_title = "Start your first quiz!"
        tip_desc  = (
            "You haven't taken any quizzes yet. Head to any module — "
            "Python, Java, SQL, DSA — and attempt a test. "
            "PrepEdge will then personalise your recommendations."
        )
    elif len(weak_areas) == 0:
        tip_title = "Great job — you're doing well! 🎉"
        tip_desc  = (
            "You've scored above 60% in all attempted topics. "
            "Keep practising to reach 80%+ and move to advanced topics."
        )
    else:
        tip_title = "Learning Path Tip"
        tip_desc  = (
            f"You have {len(weak_areas)} topic(s) that need attention. "
            "Focus on the weakest area first — improving it by even 10% "
            "has a big impact on your overall readiness."
        )

    UserRecommendation.objects.create(
        user        = user,
        topic       = None,
        rec_type    = 'tip',
        title       = tip_title,
        description = tip_desc,
        url         = '/ai/learning-path/',
        priority    = priority,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API  — called by app1/views.py after every test submission
# ─────────────────────────────────────────────────────────────────────────────

def record_quiz_attempt(user, module_or_slug: str, score: float,
                        topic_name: str = None) -> None:
    """
    Entry-point called from app1/views._save_test_result().

    Parameters
    ----------
    user         : Django User instance
    module_or_slug : module key (e.g. 'python') OR topic slug ('python-basics')
    score        : percentage score 0–100
    topic_name   : optional human-readable topic name (for auto-creating Topics)
    """
    if not user or not user.is_authenticated:
        return

    try:
        topic = _get_or_create_topic(module_or_slug, topic_name)

        UserQuizAttempt.objects.create(
            user  = user,
            topic = topic,
            score = float(score),
        )

        _refresh_weak_areas(user)
        _generate_recommendations(user)

    except Exception as exc:
        logger.warning("record_quiz_attempt failed: %s", exc)
        logger.info("Record quiz called for user: %s", user)
        print("RECORD QUIZ TRIGGERED")


# ─────────────────────────────────────────────────────────────────────────────
# VIEWS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def ai_dashboard(request):
    user = request.user

    _refresh_weak_areas(user)

    attempts = UserQuizAttempt.objects.filter(user=user)

    total_attempts = attempts.count()

    overall_accuracy = attempts.aggregate(avg=Avg('score'))['avg'] or 0
    overall_accuracy = round(overall_accuracy, 2)

    pass_count = UserQuizAttempt.objects.filter(
        user=user,
        score__gte=60
    ).count()

    pass_rate = round((pass_count / total_attempts) * 100, 2) if total_attempts else 0

    # ✅ PUT YOUR CODE HERE 👇
    topic_scores = (
        UserQuizAttempt.objects
        .filter(user=user)
        .values('topic__name')
        .annotate(avg_score=Avg('score'))
    )

    strongest_topic = None
    weakest_topic = None

    if topic_scores:
        strongest = max(topic_scores, key=lambda x: x['avg_score'])
        weakest = min(topic_scores, key=lambda x: x['avg_score'])

        if strongest['avg_score'] >= 80:
            strongest_topic = strongest['topic__name']

        if weakest['avg_score'] <= 20:
            weakest_topic = weakest['topic__name']

    topic_scores = (
    UserQuizAttempt.objects
    .filter(user=user)
    .values('topic__name')
    .annotate(avg_score=Avg('score'))
    .order_by('-avg_score')
)   

    strongest_topic = topic_scores.first()['topic__name'] if topic_scores else None
    weakest_topic = topic_scores.last()['topic__name'] if topic_scores else None

    # Weak areas
    weak_areas_qs = UserWeakArea.objects.filter(user=user).select_related('topic')

    weak_areas = [
        {
            'topic': wa.topic.name,
            'module': wa.topic.module,
            'weakness_score': wa.weakness_score,
            'reason': wa.reason
        }
        for wa in weak_areas_qs
    ]

    recommendations = UserRecommendation.objects.filter(
        user=user,
        is_dismissed=False
    ).select_related('topic')

    smart_insights = []

    if overall_accuracy < 50:
        smart_insights.append("Focus on strengthening your fundamentals.")

    if pass_rate < 60:
        smart_insights.append("Work on improving accuracy and speed.")

    if weak_areas_qs.count() > 3:
        smart_insights.append("You have multiple weak topics — prioritize revision.")

    if strongest_topic:
        smart_insights.append(f"Your strongest topic is {strongest_topic} — keep practicing it.")

    if weakest_topic:
        smart_insights.append(f"Your weakest topic is {weakest_topic} — needs immediate attention.")

    context = {
        'total_attempts': total_attempts,
        'overall_accuracy': round(overall_accuracy, 2),
        'pass_rate': pass_rate,
        'strongest_topic': strongest_topic,
        'weakest_topic': weakest_topic,
        'weak_areas': weak_areas,
        'recommendations': recommendations,
        'smart_insights': smart_insights,
        'recent_attempts': attempts.order_by('-attempted_at')[:5],
    }

    return render(request, 'ai/dashboard.html', context)
@login_required
@require_POST
def refresh_recommendations(request):
    """Manually trigger recommendation regeneration."""
    user = request.user
    _refresh_weak_areas(user)
    _generate_recommendations(user)
    return redirect('ai_dashboard')


@login_required
@require_POST
def dismiss_recommendation(request, rec_id):
    """Mark a single recommendation as dismissed."""
    rec = get_object_or_404(UserRecommendation, id=rec_id, user=request.user)
    rec.is_dismissed = True
    rec.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    return redirect('ai_dashboard')

@login_required
@login_required
def weak_areas_detail(request):
    user = request.user

    weak_areas = (
        UserWeakArea.objects
        .filter(user=user)
        .select_related('topic')
        .order_by('-weakness_score')
    )

    by_module = {}

    for wa in weak_areas:
        module = wa.topic.module

        if module not in by_module:
            by_module[module] = []

        by_module[module].append({
            "topic": wa.topic,
            "weakness_score": wa.weakness_score,
            "reason": wa.reason,
            "last_updated": wa.last_updated,
        })

    return render(request, "weak_areas.html", {
        "by_module": by_module
    })
@login_required
def learning_path(request):
    """
    Shows a suggested learning order based on weak areas and prerequisites.
    Topics with highest weakness scores come first.
    """
    user = request.user

    weak_areas = (
        UserWeakArea.objects
        .filter(user=user)
        .select_related('topic')
        .order_by('-weakness_score')
    )

    # Build a prioritised path: weak topics first, then strong ones
    attempted_topic_ids = set(
        UserQuizAttempt.objects.filter(user=user).values_list('topic_id', flat=True)
    )
    unattempted_topics = (
        Topic.objects
        .exclude(id__in=attempted_topic_ids)
        .order_by('difficulty', 'module')[:5]
    )

    context = {
        'weak_areas':         weak_areas,
        'unattempted_topics': unattempted_topics,
    }
    return render(request, 'ai/learning_path.html', context)


@login_required
def recommendations_api(request):
    """JSON endpoint for dashboard widgets."""
    user = request.user

    recs = (
        UserRecommendation.objects
        .filter(user=user, is_dismissed=False)
        .select_related('topic')
        .order_by('priority')[:10]
    )

    data = [
        {
            'id':          r.id,
            'type':        r.rec_type,
            'title':       r.title,
            'description': r.description,
            'url':         r.url,
            'priority':    r.priority,
            'topic':       r.topic.name if r.topic else None,
        }
        for r in recs
    ]
    return JsonResponse({'recommendations': data})


@login_required
@csrf_exempt
def record_score(request):
    """
    AJAX POST endpoint — test pages can call this directly.
    Expected JSON body: { "module": "python", "score": 75.0, "topic_name": "Python Basics" }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        body   = json.loads(request.body)
        module = body.get('module', '')
        score  = float(body.get('score', 0))
        name   = body.get('topic_name', '')
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    record_quiz_attempt(request.user, module, score, name)
    return JsonResponse({'status': 'ok', 'module': module, 'score': score})


def ai_recommendations(request):
    return render(request, 'ai/dashboard')