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
WEAK_THRESHOLD   = 60.0   # below this → weak area
STRONG_THRESHOLD = 80.0   # above this → strength

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


def _refresh_weak_areas(user) -> None:
    """
    Recompute UserWeakArea rows for this user based on ALL their quiz attempts.

    weakness_score formula
    ─────────────────────
    For each topic the user has attempted:
        avg_score    = average of all attempt scores (0–100)
        attempt_pen  = penalty for few attempts  (max 0.2 if only 1 attempt)
        weakness_score = clamp(1 - avg_score/100 + attempt_pen, 0.0, 1.0)

    High weakness_score → very weak.  Low → strong.
    """
    attempts = (
        UserQuizAttempt.objects
        .filter(user=user)
        .values('topic')
        .annotate(
            avg_score=Avg('score'),
            total=Count('id'),
        )
    )

    for row in attempts:
        topic_id  = row['topic']
        avg_score = row['avg_score'] or 0
        total     = row['total']

        # Small penalty if the user has only 1-2 attempts (less data confidence)
        attempt_penalty = max(0, (3 - total) * 0.07)   # 0.14, 0.07, 0 for 1,2,3+ attempts

        raw_weakness = 1.0 - (avg_score / 100.0) + attempt_penalty
        weakness_score = round(min(max(raw_weakness, 0.0), 1.0), 3)

        # Build a human-readable reason
        if avg_score < WEAK_THRESHOLD:
            reason = f"Average score {avg_score:.1f}% across {total} attempt(s) — needs revision"
        elif avg_score < STRONG_THRESHOLD:
            reason = f"Average score {avg_score:.1f}% — approaching proficiency"
        else:
            reason = f"Average score {avg_score:.1f}% — strong performance"

        UserWeakArea.objects.update_or_create(
            user=user,
            topic_id=topic_id,
            defaults={
                'weakness_score': weakness_score,
                'reason':         reason,
            }
        )


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

    weak_areas = (
        UserWeakArea.objects
        .filter(user=user, weakness_score__gt=0.4)
        .select_related('topic')
        .order_by('-weakness_score')[:8]
    )

    priority = 1

    for wa in weak_areas:
        topic       = wa.topic
        score_pct   = round((1 - wa.weakness_score) * 100, 1)
        module_name = topic.get_module_display() if hasattr(topic, 'get_module_display') else topic.module.title()

        # ── Recommendation A: Revisit topic ──────────────────────────────
        UserRecommendation.objects.create(
            user        = user,
            topic       = topic,
            rec_type    = 'topic',
            title       = f"Revisit {topic.name}",
            description = (
                f"Your average score in {topic.name} is around {score_pct}%. "
                f"Reviewing the core concepts will help solidify your understanding. "
                f"{wa.reason}"
            ),
            url         = topic.resource_url or f"/{topic.module}/",
            priority    = priority,
        )
        priority += 1

        # ── Recommendation B: Practice exercise (only if very weak) ──────
        if wa.weakness_score > 0.55:
            UserRecommendation.objects.create(
                user        = user,
                topic       = topic,
                rec_type    = 'exercise',
                title       = f"Practice {topic.name} Exercises",
                description = (
                    f"Hands-on practice is the fastest way to improve in {topic.name}. "
                    f"Try the practice set to boost your confidence."
                ),
                url         = f"/{topic.module}/practice/",
                priority    = priority,
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


# ─────────────────────────────────────────────────────────────────────────────
# VIEWS
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def ai_dashboard(request):
    """
    Main AI Recommendations dashboard.
    Shows weak areas, recommendations, and a performance summary.
    """
    user = request.user

    # Pull data
    recommendations = (
        UserRecommendation.objects
        .filter(user=user, is_dismissed=False)
        .select_related('topic')
        .order_by('priority', '-created_at')[:10]
    )

    weak_areas = (
        UserWeakArea.objects
        .filter(user=user)
        .select_related('topic')
        .order_by('-weakness_score')[:6]
    )

    total_attempts = UserQuizAttempt.objects.filter(user=user).count()

    # Build module-level performance summary from app1's TestResult
    # (works even if ai_recommendations Topics aren't fully seeded)
    try:
        from app1.models import TestResult
        module_stats = (
            TestResult.objects
            .filter(user=user)
            .values('test__language')
            .annotate(avg=Avg('score'), attempts=Count('id'))
            .order_by('test__language')
        )
    except Exception:
        module_stats = []

    has_data = total_attempts > 0 or bool(module_stats)

    context = {
        'recommendations': recommendations,
        'weak_areas':      weak_areas,
        'total_attempts':  total_attempts,
        'module_stats':    module_stats,
        'has_data':        has_data,
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
def weak_areas_detail(request):
    """Detailed breakdown of all weak areas with score history."""
    user = request.user

    weak_areas = (
        UserWeakArea.objects
        .filter(user=user)
        .select_related('topic')
        .order_by('-weakness_score')
    )

    # Attach recent attempt history to each weak area
    enriched = []
    for wa in weak_areas:
        attempts = (
            UserQuizAttempt.objects
            .filter(user=user, topic=wa.topic)
            .order_by('-attempted_at')[:5]
        )
        enriched.append({
            'weak_area': wa,
            'attempts':  attempts,
            'pct_score': round((1 - wa.weakness_score) * 100, 1),
        })

    context = {
        'enriched':    enriched,
        'total_topics': weak_areas.count(),
    }
    return render(request, 'ai/weak_areas.html', context)


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
    return render(request, 'ai.html')