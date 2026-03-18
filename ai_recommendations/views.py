from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Avg, Count, Max, Min

from .ai_engine import RecommendationEngine
from .models import (
    UserQuizAttempt,
    UserWeakArea,
    UserRecommendation,
    Topic,
    UserPracticeCompletion,
)


# ─────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────

def _compute_performance_summary(user):
    """
    Returns a dict with:
      overall_accuracy  – float (rounded %) or None
      total_attempts    – int
      strongest_topic   – str or None
      weakest_topic     – str or None
      smart_insights    – list of str
    """
    attempts_qs = UserQuizAttempt.objects.filter(user=user)
    total_attempts = attempts_qs.count()

    if total_attempts == 0:
        return {
            'overall_accuracy': None,
            'total_attempts':   0,
            'strongest_topic':  None,
            'weakest_topic':    None,
            'smart_insights':   [],
        }

    # Overall accuracy = mean of all quiz scores
    overall_accuracy = round(
        attempts_qs.aggregate(avg=Avg('score'))['avg'] or 0, 1
    )

    # Per-topic averages to find strongest / weakest
    topic_avgs = (
        attempts_qs
        .values('topic__name')
        .annotate(avg_score=Avg('score'), attempts=Count('id'))
        .order_by('-avg_score')
    )

    strongest_topic = topic_avgs.first()['topic__name'] if topic_avgs.exists() else None
    weakest_topic   = topic_avgs.last()['topic__name']  if topic_avgs.count() > 1 else None

    # ── Smart Insights (rule-based NLG) ─────────────────────────
    insights = []
    pass_rate = attempts_qs.filter(score__gte=60).count() / total_attempts * 100

    if pass_rate < 50:
        insights.append(
            f"Your pass rate is {pass_rate:.0f}% — focus on reviewing topics "
            f"before retaking quizzes."
        )
    elif pass_rate >= 80:
        insights.append(
            f"Excellent! You're passing {pass_rate:.0f}% of your quizzes. "
            f"Push yourself with advanced topics."
        )

    if weakest_topic:
        # Estimate score impact: if weakest topic avg is low, estimate improvement
        weakest_avg = topic_avgs.last()['avg_score'] or 0
        potential_gain = round((60 - weakest_avg) / 100 * 15, 1)
        if weakest_avg < 60:
            insights.append(
                f"Improving {weakest_topic} (currently {weakest_avg:.0f}%) "
                f"could boost your overall score by ~{potential_gain}%."
            )

    if total_attempts >= 5:
        # Check if theory vs coding topics differ (simple heuristic by module)
        coding_modules  = ['python', 'java', 'cpp', 'javascript', 'dsa']
        theory_modules  = ['sql', 'communication', 'soft_skills']

        coding_avg = (
            attempts_qs.filter(topic__module__in=coding_modules)
            .aggregate(avg=Avg('score'))['avg'] or 0
        )
        theory_avg = (
            attempts_qs.filter(topic__module__in=theory_modules)
            .aggregate(avg=Avg('score'))['avg'] or 0
        )

        if coding_avg and theory_avg:
            if theory_avg - coding_avg > 10:
                insights.append(
                    f"You perform better in theory ({theory_avg:.0f}%) "
                    f"than coding ({coding_avg:.0f}%). "
                    f"Practice more coding exercises to close the gap."
                )
            elif coding_avg - theory_avg > 10:
                insights.append(
                    f"You perform better in coding ({coding_avg:.0f}%) "
                    f"than theory ({theory_avg:.0f}%). "
                    f"Review communication and SQL topics."
                )

    if not insights:
        insights.append(
            "Keep taking quizzes regularly — consistency is the key to interview success."
        )

    return {
        'overall_accuracy': overall_accuracy,
        'total_attempts':   total_attempts,
        'strongest_topic':  strongest_topic,
        'weakest_topic':    weakest_topic,
        'smart_insights':   insights,
    }


def _enrich_weak_areas(weak_areas_qs, user):
    """
    Attaches avg_score and estimated_accuracy to each UserWeakArea object
    so the template can display them directly.
    """
    # Build a map: topic_id → avg_score from quiz attempts
    score_map = {
        row['topic_id']: round(row['avg_score'], 1)
        for row in (
            UserQuizAttempt.objects
            .filter(user=user)
            .values('topic_id')
            .annotate(avg_score=Avg('score'))
        )
    }

    enriched = []
    for wa in weak_areas_qs:
        wa.avg_score = score_map.get(wa.topic_id)
        # Estimated accuracy shown when no quiz data: (1 - weakness_score) * 100
        wa.estimated_accuracy = round((1 - wa.weakness_score) * 100)
        enriched.append(wa)

    return enriched


# ─────────────────────────────────────────────────────────────────
# VIEW: AI Dashboard  →  renders ai.html
# URL:  /ai/dashboard/   name='ai_dashboard'
# ─────────────────────────────────────────────────────────────────

@login_required
def ai_dashboard(request):
    """
    Main AI Recommendations page.

    Context variables passed to ai.html
    ─────────────────────────────────────
    overall_accuracy  : float | None   e.g. 72.5
    total_attempts    : int            e.g. 12
    strongest_topic   : str | None     e.g. "DBMS"
    weakest_topic     : str | None     e.g. "Recursion"
    weak_areas        : list[UserWeakArea]  each enriched with .avg_score
    recommendations   : QuerySet[UserRecommendation]
    smart_insights    : list[str]
    """
    user = request.user

    # ① Performance summary (computed fresh from quiz attempts)
    summary = _compute_performance_summary(user)

    # ② Weak areas (from pre-computed UserWeakArea table)
    #    If empty, trigger a fresh engine run automatically on first visit
    weak_areas_qs = (
        UserWeakArea.objects
        .filter(user=user)
        .select_related('topic')
        .order_by('-weakness_score')
    )

    if not weak_areas_qs.exists() and summary['total_attempts'] > 0:
        # Auto-generate on first visit if user has data but no computed rows yet
        engine = RecommendationEngine(user)
        engine.run(save_to_db=True)
        weak_areas_qs = (
            UserWeakArea.objects
            .filter(user=user)
            .select_related('topic')
            .order_by('-weakness_score')
        )

    weak_areas = _enrich_weak_areas(list(weak_areas_qs), user)

    # ③ Recommendations
    recommendations = (
        UserRecommendation.objects
        .filter(user=user, is_dismissed=False)
        .select_related('topic')
        .order_by('priority')
    )

    context = {
        # Performance summary
        'overall_accuracy': summary['overall_accuracy'],
        'total_attempts':   summary['total_attempts'],
        'strongest_topic':  summary['strongest_topic'],
        'weakest_topic':    summary['weakest_topic'],

        # Table data
        'weak_areas':       weak_areas,

        # Recommendations grid
        'recommendations':  recommendations,

        # Smart insights list
        'smart_insights':   summary['smart_insights'],

        # Page meta
        'page_title':       'AI Recommendations',
    }

    return render(request, 'ai.html', context)


# ─────────────────────────────────────────────────────────────────
# VIEW: Refresh Recommendations  (POST)
# URL:  /ai/refresh/   name='ai_refresh'
# ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def refresh_recommendations(request):
    """Recomputes weaknesses + recommendations and saves to DB."""
    engine = RecommendationEngine(request.user)
    result = engine.run(save_to_db=True)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status':     'ok',
            'count':      len(result['recommendations']),
            'weak_count': len(result['weaknesses']),
        })

    messages.success(request, "Recommendations refreshed!")
    return redirect('ai_dashboard')


# ─────────────────────────────────────────────────────────────────
# VIEW: Dismiss Recommendation  (POST)
# URL:  /ai/dismiss/<int:rec_id>/   name='ai_dismiss'
# ─────────────────────────────────────────────────────────────────

@login_required
@require_POST
def dismiss_recommendation(request, rec_id):
    rec = get_object_or_404(UserRecommendation, id=rec_id, user=request.user)
    rec.is_dismissed = True
    rec.save(update_fields=['is_dismissed'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'dismissed'})

    return redirect('ai_dashboard')


# ─────────────────────────────────────────────────────────────────
# HELPERS: record quiz / practice (call from existing views)
# ─────────────────────────────────────────────────────────────────

def record_quiz_attempt(user, topic_slug: str, score: float, wrong_topics: list = None):
    """
    Call this from your existing quiz-submit views.

    Example (in app1/views.py, your python_test submit handler):
        from ai_recommendations.views import record_quiz_attempt
        record_quiz_attempt(request.user, 'python-oop', score=72.5)
    """
    topic = Topic.objects.filter(slug=topic_slug).first()
    if topic is None:
        return
    UserQuizAttempt.objects.create(
        user=user, topic=topic, score=score,
        wrong_topics=wrong_topics or [],
    )


def record_practice_completion(user, topic_slug: str, exercise_count: int = 1):
    """
    Call this from your practice completion views.

    Example:
        from ai_recommendations.views import record_practice_completion
        record_practice_completion(request.user, 'dsa-sorting', exercise_count=3)
    """
    topic = Topic.objects.filter(slug=topic_slug).first()
    if topic is None:
        return
    obj, created = UserPracticeCompletion.objects.get_or_create(
        user=user, topic=topic,
        defaults={'exercise_count': exercise_count}
    )
    if not created:
        obj.exercise_count += exercise_count
        obj.save(update_fields=['exercise_count', 'completed_at'])
 
# ─────────────────────────────────────────────────────────────────
# VIEW: Weak Areas Detail
# URL:  /ai/weak-areas/   name='ai_weak_areas'
# ─────────────────────────────────────────────────────────────────
 
@login_required
def weak_areas_detail(request):
    weak_areas = (
        UserWeakArea.objects
        .filter(user=request.user)
        .select_related('topic')
        .order_by('-weakness_score')
    )
    by_module = {}
    for wa in weak_areas:
        mod = wa.topic.get_module_display()
        by_module.setdefault(mod, []).append(wa)
 
    return render(request, 'ai/weak_areas.html', {
        'by_module': by_module,
        'page_title': 'My Weak Areas',
    })
 
 
# ─────────────────────────────────────────────────────────────────
# VIEW: Learning Path
# URL:  /ai/learning-path/   name='ai_learning_path'
# ─────────────────────────────────────────────────────────────────
 
@login_required
def learning_path(request):
    from .ai_engine import LearningPathBuilder, WeaknessAnalyzer
    weaknesses = WeaknessAnalyzer(request.user).weak_topics(top_n=15)
    path_slugs = LearningPathBuilder().build(weaknesses)
    topic_map  = {t.slug: t for t in Topic.objects.filter(slug__in=path_slugs)}
    path_topics = [topic_map[s] for s in path_slugs if s in topic_map]
 
    return render(request, 'ai/learning_path.html', {
        'path_topics': path_topics,
        'page_title':  'Your Learning Path',
    })
 
 
# ─────────────────────────────────────────────────────────────────
# VIEW: JSON API
# URL:  /ai/api/recommendations/   name='ai_recommendations_api'
# ─────────────────────────────────────────────────────────────────
 
@login_required
def recommendations_api(request):
    recs = (
        UserRecommendation.objects
        .filter(user=request.user, is_dismissed=False)
        .select_related('topic')
        .order_by('priority')[:5]
    )
    data = [
        {
            'id':          r.id,
            'type':        r.rec_type,
            'title':       r.title,
            'description': r.description,
            'url':         r.url,
            'topic':       r.topic.name if r.topic else None,
            'priority':    r.priority,
        }
        for r in recs
    ]
    return JsonResponse({'recommendations': data})
 
 
# ─────────────────────────────────────────────────────────────────
# VIEW: Record Score from test page JS (AJAX POST)
# URL:  /ai/record-score/   name='ai_record_score'
# Called automatically by the score reporter injected in test pages
# ─────────────────────────────────────────────────────────────────
 
import json
 
@require_POST
def record_score(request):
    """
    Receives { topic: 'python-basics', score: 75 } from test page JS.
    Saves a UserQuizAttempt. User must be logged in (checked via cookie,
    anonymous posts are silently ignored).
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'ignored'}, status=200)
 
    try:
        data  = json.loads(request.body)
        slug  = str(data.get('topic', '')).strip()
        score = float(data.get('score', 0))
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({'status': 'error', 'msg': 'bad payload'}, status=400)
 
    if not slug or not (0 <= score <= 100):
        return JsonResponse({'status': 'error', 'msg': 'invalid data'}, status=400)
 
    topic = Topic.objects.filter(slug=slug).first()
    if topic is None:
        return JsonResponse({'status': 'ignored', 'msg': f'unknown topic: {slug}'}, status=200)
 
    UserQuizAttempt.objects.create(
        user  = request.user,
        topic = topic,
        score = score,
    )
    return JsonResponse({'status': 'ok', 'topic': slug, 'score': score})
 