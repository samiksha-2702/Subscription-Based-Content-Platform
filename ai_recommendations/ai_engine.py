from __future__ import annotations
 
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
 
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Max
from django.urls import reverse
from django.utils import timezone
 
# ── Lazy imports so this file works even before migrations run ──────────────
def _models():
    from ai_recommendations import models as m   # ← was: from . import models
    return m
 
 
# ═══════════════════════════════════════════════════════════════════
# DATA CLASSES  (plain Python, no DB dependency)
# ═══════════════════════════════════════════════════════════════════
 
@dataclass
class TopicWeakness:
    topic_slug:     str
    topic_name:     str
    module:         str
    weakness_score: float          # 0.0 = strong, 1.0 = very weak
    avg_score:      float | None   # latest average quiz score (%)
    attempts:       int
    practiced:      bool
    reason:         str
 
 
@dataclass
class Recommendation:
    rec_type:    str                # 'topic' | 'exercise' | 'article' | 'path' | 'tip'
    title:       str
    description: str
    url:         str
    priority:    int               # 1 = most urgent
    topic_slug:  str | None = None
 
 
# ═══════════════════════════════════════════════════════════════════
# 1. WEAKNESS ANALYZER
# ═══════════════════════════════════════════════════════════════════
 
class WeaknessAnalyzer:
    """
    Analyses a single user's performance data and returns
    a list of TopicWeakness objects, sorted by weakness_score desc.
 
    Scoring formula
    ───────────────
    base_score      = 1 - (avg_quiz_score / 100)   [0=aced, 1=failed everything]
    attempt_bonus   = decay if never attempted      [+0.3 if 0 attempts]
    practice_bonus  = +0.2 if never practised
    recency_penalty = +0.1 if last attempt > 14 days ago
 
    Final weakness_score is clamped to [0.0, 1.0].
    """
 
    # Thresholds
    LOW_SCORE_THRESHOLD   = 60.0   # % – below this = weak
    HIGH_SCORE_THRESHOLD  = 80.0   # % – above this = strong
    STALE_DAYS            = 14     # days before a topic is considered "stale"
 
    def __init__(self, user: User):
        self.user = user
        m = _models()
        self.Topic                  = m.Topic
        self.UserQuizAttempt        = m.UserQuizAttempt
        self.UserPracticeCompletion = m.UserPracticeCompletion
 
    # ── public API ──────────────────────────────────────────────────
 
    def analyze(self) -> List[TopicWeakness]:
        """Return TopicWeakness list for every topic the user has touched,
           plus topics they have *never* touched (unattempted = weak by default)."""
        attempted  = self._attempted_topics()
        practiced  = self._practiced_slugs()
        all_topics = list(self.Topic.objects.all())
 
        results: List[TopicWeakness] = []
        for topic in all_topics:
            info = attempted.get(topic.slug, {})
            tw   = self._score_topic(topic, info, practiced)
            results.append(tw)
 
        results.sort(key=lambda x: x.weakness_score, reverse=True)
        return results
 
    def weak_topics(self, top_n: int = 8) -> List[TopicWeakness]:
        """Return the top-N weakest topics."""
        return [t for t in self.analyze() if t.weakness_score > 0.3][:top_n]
 
    # ── private helpers ─────────────────────────────────────────────
 
    def _attempted_topics(self) -> Dict[str, dict]:
        """
        Returns {topic_slug: {avg_score, attempts, last_attempted}} 
        from UserQuizAttempt aggregation.
        """
        qs = (
            self.UserQuizAttempt.objects
            .filter(user=self.user)
            .values('topic__slug')
            .annotate(
                avg_score=Avg('score'),
                attempts=Count('id'),
                last_attempted=Max('attempted_at'),
            )
        )
        return {
            row['topic__slug']: {
                'avg_score':      row['avg_score'],
                'attempts':       row['attempts'],
                'last_attempted': row['last_attempted'],
            }
            for row in qs
        }
 
    def _practiced_slugs(self) -> set:
        """Returns set of topic slugs the user has practiced."""
        return set(
            self.UserPracticeCompletion.objects
            .filter(user=self.user)
            .values_list('topic__slug', flat=True)
        )
 
    def _score_topic(
        self,
        topic,
        info: dict,
        practiced: set,
    ) -> TopicWeakness:
        avg_score       = info.get('avg_score')
        attempts        = info.get('attempts', 0)
        last_attempted  = info.get('last_attempted')
        is_practiced    = topic.slug in practiced
 
        # ── base weakness from quiz score ──
        if avg_score is None:
            base = 0.7   # never attempted → assumed weak
            reason = "Never attempted this quiz"
        elif avg_score < self.LOW_SCORE_THRESHOLD:
            base = 1.0 - (avg_score / 100)
            reason = f"Low average score ({avg_score:.1f}%)"
        elif avg_score < self.HIGH_SCORE_THRESHOLD:
            base = 0.3
            reason = f"Moderate score ({avg_score:.1f}%) – room for improvement"
        else:
            base = 0.1
            reason = f"Strong score ({avg_score:.1f}%)"
 
        # ── bonuses ──
        practice_bonus = 0.0 if is_practiced else 0.15
        stale_bonus    = 0.0
 
        if last_attempted:
            days_ago = (timezone.now() - last_attempted).days
            if days_ago > self.STALE_DAYS:
                stale_bonus = min(0.1, days_ago / 365)  # max +0.1 per year
 
        weakness_score = min(1.0, base + practice_bonus + stale_bonus)
 
        return TopicWeakness(
            topic_slug     = topic.slug,
            topic_name     = topic.name,
            module         = topic.module,
            weakness_score = round(weakness_score, 3),
            avg_score      = avg_score,
            attempts       = attempts,
            practiced      = is_practiced,
            reason         = reason,
        )
 
 
# ═══════════════════════════════════════════════════════════════════
# 2. RULE-BASED RECOMMENDER
# ═══════════════════════════════════════════════════════════════════
 
class RuleBasedRecommender:
    """
    Converts TopicWeakness list into actionable Recommendation objects.
 
    Rules (priority order):
      R1 – Score < 40%  → "Revisit Basics" + practice exercise
      R2 – 40–60%       → Targeted practice exercise
      R3 – Never tried  → Encourage first attempt
      R4 – Stale topic  → Refresh reminder
      R5 – Strong areas → Suggest advanced content (positive reinforcement)
    """
 
    # URL patterns – adjust to match your actual URL names
    URL_PATTERNS = {
        'quiz':     '/{module}/{topic}/quiz/',
        'practice': '/{module}/{topic}/practice/',
        'notes':    '/{module}/{topic}/notes/',
        'advanced': '/{module}/{topic}/advanced/',
    }
 
    def generate(self, weaknesses: List[TopicWeakness]) -> List[Recommendation]:
        recs: List[Recommendation] = []
 
        for tw in weaknesses:
            if tw.attempts == 0:
                recs.extend(self._rule_never_tried(tw))
            elif tw.avg_score is not None and tw.avg_score < 40:
                recs.extend(self._rule_very_weak(tw))
            elif tw.avg_score is not None and tw.avg_score < 60:
                recs.extend(self._rule_moderate(tw))
            elif not tw.practiced:
                recs.extend(self._rule_needs_practice(tw))
 
        # Deduplicate by (topic_slug, rec_type)
        seen = set()
        unique: List[Recommendation] = []
        for r in recs:
            key = (r.topic_slug, r.rec_type)
            if key not in seen:
                seen.add(key)
                unique.append(r)
 
        unique.sort(key=lambda x: x.priority)
        return unique
 
    # ── individual rules ────────────────────────────────────────────
 
    def _rule_very_weak(self, tw: TopicWeakness) -> List[Recommendation]:
        return [
            Recommendation(
                rec_type    = 'topic',
                title       = f"🔁 Revisit {tw.topic_name} Basics",
                description = (
                    f"Your average score in {tw.topic_name} is {tw.avg_score:.1f}%, "
                    f"which is below the passing threshold. "
                    f"Start from the fundamentals and rebuild your understanding."
                ),
                url         = self._url('notes', tw),
                priority    = 1,
                topic_slug  = tw.topic_slug,
            ),
            Recommendation(
                rec_type    = 'exercise',
                title       = f"📝 Practice Exercises: {tw.topic_name}",
                description = (
                    f"Hands-on practice is the fastest way to improve. "
                    f"Complete at least 5 exercises in {tw.topic_name} before retrying the quiz."
                ),
                url         = self._url('practice', tw),
                priority    = 2,
                topic_slug  = tw.topic_slug,
            ),
        ]
 
    def _rule_moderate(self, tw: TopicWeakness) -> List[Recommendation]:
        return [
            Recommendation(
                rec_type    = 'exercise',
                title       = f"⚡ Level Up: {tw.topic_name} Practice",
                description = (
                    f"You scored {tw.avg_score:.1f}% in {tw.topic_name}. "
                    f"You're on the right track — targeted practice will push you above 80%."
                ),
                url         = self._url('practice', tw),
                priority    = 3,
                topic_slug  = tw.topic_slug,
            ),
        ]
 
    def _rule_never_tried(self, tw: TopicWeakness) -> List[Recommendation]:
        return [
            Recommendation(
                rec_type    = 'topic',
                title       = f"🚀 Get Started: {tw.topic_name}",
                description = (
                    f"You haven't explored {tw.topic_name} yet. "
                    f"This is a key topic in the {tw.module.replace('_',' ').title()} module. "
                    f"Start with the notes and take the quiz when ready."
                ),
                url         = self._url('notes', tw),
                priority    = 4,
                topic_slug  = tw.topic_slug,
            ),
        ]
 
    def _rule_needs_practice(self, tw: TopicWeakness) -> List[Recommendation]:
        return [
            Recommendation(
                rec_type    = 'exercise',
                title       = f"🛠️ Practice {tw.topic_name} – Reinforce Your Knowledge",
                description = (
                    f"You've passed the quiz in {tw.topic_name} but haven't completed any "
                    f"practice exercises. Practicing will cement your understanding."
                ),
                url         = self._url('practice', tw),
                priority    = 5,
                topic_slug  = tw.topic_slug,
            ),
        ]
 
    def _url(self, kind: str, tw: TopicWeakness) -> str:
        pattern = self.URL_PATTERNS.get(kind, '/')
        return pattern.format(module=tw.module, topic=tw.topic_slug)
 
 
# ═══════════════════════════════════════════════════════════════════
# 3. LEARNING PATH BUILDER
# ═══════════════════════════════════════════════════════════════════
 
class LearningPathBuilder:
    """
    Builds a topologically-sorted learning path for a user's weak areas,
    respecting prerequisite relationships between topics.
 
    Returns an ordered list of topic slugs.
    """
 
    def build(self, weaknesses: List[TopicWeakness]) -> List[str]:
        m = _models()
        weak_slugs  = {tw.topic_slug for tw in weaknesses if tw.weakness_score > 0.4}
        if not weak_slugs:
            return []
 
        topics = {
            t.slug: t
            for t in m.Topic.objects.prefetch_related('prerequisites')
            .filter(slug__in=weak_slugs)
        }
 
        # Build adjacency list: slug → [prereq_slug, ...]
        graph: Dict[str, List[str]] = {slug: [] for slug in weak_slugs}
        for slug, topic in topics.items():
            for prereq in topic.prerequisites.all():
                if prereq.slug in weak_slugs:
                    graph[slug].append(prereq.slug)
 
        return self._topological_sort(graph)
 
    # ── Kahn's algorithm ─────────────────────────────────────────────
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        in_degree = defaultdict(int)
        for node, deps in graph.items():
            if node not in in_degree:
                in_degree[node] = 0
            for dep in deps:
                in_degree[dep] += 0   # ensure it's in dict
                in_degree[node] += 1  # node depends on dep → dep comes first
 
        queue = [n for n, d in in_degree.items() if d == 0]
        result = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            # reduce in-degree for nodes that depend on `node`
            for n, deps in graph.items():
                if node in deps:
                    in_degree[n] -= 1
                    if in_degree[n] == 0:
                        queue.append(n)
 
        return result
 
 
# ═══════════════════════════════════════════════════════════════════
# 4. AI TIP GENERATOR  (rule-based NLG)
# ═══════════════════════════════════════════════════════════════════
 
class AITipGenerator:
    """
    Generates human-readable improvement tips based on performance patterns.
    Pure rule-based — can be swapped with an LLM call later.
    """
 
    TIPS = {
        'python': [
            "Practice writing Pythonic code using list comprehensions and generators.",
            "Review Python's standard library — knowing the right module saves hours.",
            "Study decorators and context managers to write cleaner Python.",
        ],
        'java': [
            "Focus on understanding Java's OOP pillars: encapsulation, inheritance, and polymorphism.",
            "Practice exception handling and the Java Collections Framework.",
            "Study generics and lambda expressions for modern Java programming.",
        ],
        'cpp': [
            "Understand memory management: pointers, references, and RAII.",
            "Review STL containers and algorithms — they appear in interviews often.",
            "Practice writing const-correct, memory-safe code.",
        ],
        'javascript': [
            "Master asynchronous JavaScript: callbacks, Promises, and async/await.",
            "Review closure and the event loop — these are common interview questions.",
            "Study ES6+ features: destructuring, spread, and template literals.",
        ],
        'sql': [
            "Practice complex JOINs with real datasets — they're tested in every data role.",
            "Study window functions (ROW_NUMBER, RANK, LEAD, LAG) for analytics queries.",
            "Understand query execution plans to write performant SQL.",
        ],
        'dsa': [
            "Implement classic algorithms from scratch, not just read about them.",
            "Study time complexity for each data structure operation.",
            "Practice BFS/DFS problems — they underpin most graph interview questions.",
        ],
        'communication': [
            "Record yourself answering mock interview questions and review the footage.",
            "Use the STAR method (Situation, Task, Action, Result) for behavioural answers.",
            "Practice active listening: summarise what the interviewer said before answering.",
        ],
        'soft_skills': [
            "Prepare 2–3 strong examples per competency (leadership, conflict, teamwork).",
            "Research the company culture before every interview.",
            "Arrive 5 minutes early, whether virtual or in-person.",
        ],
    }
 
    DEFAULT_TIPS = [
        "Consistency beats intensity — study for 30 minutes daily rather than cramming.",
        "After each quiz, review every wrong answer before moving on.",
        "Teach a concept to someone else (or write about it) to truly understand it.",
    ]
 
    def get_tip(self, module: str) -> str:
        tips = self.TIPS.get(module, self.DEFAULT_TIPS)
        # In production you could use random.choice; here we use hash for determinism
        idx  = hash(module) % len(tips)
        return tips[idx]
 
    def generate_for_weaknesses(self, weaknesses: List[TopicWeakness]) -> List[Recommendation]:
        seen_modules = set()
        recs = []
        for tw in weaknesses[:5]:   # top 5 weak areas
            if tw.module not in seen_modules:
                seen_modules.add(tw.module)
                tip = self.get_tip(tw.module)
                recs.append(Recommendation(
                    rec_type    = 'tip',
                    title       = f"💡 AI Tip: {tw.module.replace('_',' ').title()}",
                    description = tip,
                    url         = '',
                    priority    = 6,
                    topic_slug  = tw.topic_slug,
                ))
        return recs
 
 
# ═══════════════════════════════════════════════════════════════════
# 5. RECOMMENDATION ENGINE  (façade / entry point)
# ═══════════════════════════════════════════════════════════════════
 
class RecommendationEngine:
    """
    Main entry point.  Call engine.run() to refresh all recommendations
    for a user in a single transaction-friendly operation.
 
    Example
    -------
    from app1.ai_engine import RecommendationEngine
 
    engine = RecommendationEngine(request.user)
    result = engine.run()
    # result = {
    #   'weaknesses':       [TopicWeakness, ...],
    #   'recommendations':  [Recommendation, ...],
    #   'learning_path':    ['python-basics', 'python-oop', ...],
    # }
    """
 
    def __init__(self, user: User):
        self.user       = user
        self.analyzer   = WeaknessAnalyzer(user)
        self.recommender = RuleBasedRecommender()
        self.path_builder = LearningPathBuilder()
        self.tip_generator = AITipGenerator()
 
    # ── public API ──────────────────────────────────────────────────
 
    def run(self, save_to_db: bool = True) -> dict:
        """Compute weaknesses, generate recs, optionally persist to DB."""
 
        weaknesses      = self.analyzer.weak_topics(top_n=10)
        rule_recs       = self.recommender.generate(weaknesses)
        ai_tips         = self.tip_generator.generate_for_weaknesses(weaknesses)
        all_recs        = rule_recs + ai_tips
        learning_path   = self.path_builder.build(weaknesses)
 
        if save_to_db:
            self._persist_weaknesses(weaknesses)
            self._persist_recommendations(all_recs)
 
        return {
            'weaknesses':      weaknesses,
            'recommendations': all_recs,
            'learning_path':   learning_path,
        }
 
    def get_dashboard_data(self) -> dict:
        """
        Lightweight call for the dashboard — reads from pre-computed DB rows
        instead of recomputing from scratch every page load.
        """
        m = _models()
        weak_areas = (
            m.UserWeakArea.objects
            .filter(user=self.user, weakness_score__gt=0.3)
            .select_related('topic')
            .order_by('-weakness_score')[:5]
        )
        recommendations = (
            m.UserRecommendation.objects
            .filter(user=self.user, is_dismissed=False)
            .select_related('topic')
            .order_by('priority')[:8]
        )
        return {
            'weak_areas':      weak_areas,
            'recommendations': recommendations,
        }
 
    # ── DB persistence helpers ───────────────────────────────────────
 
    def _persist_weaknesses(self, weaknesses: List[TopicWeakness]) -> None:
        m = _models()
        topic_map = {
            t.slug: t
            for t in m.Topic.objects.filter(slug__in=[w.topic_slug for w in weaknesses])
        }
        for tw in weaknesses:
            topic = topic_map.get(tw.topic_slug)
            if topic is None:
                continue
            m.UserWeakArea.objects.update_or_create(
                user=self.user, topic=topic,
                defaults={
                    'weakness_score': tw.weakness_score,
                    'reason':         tw.reason,
                }
            )
 
    def _persist_recommendations(self, recs: List[Recommendation]) -> None:
        m = _models()
        # Clear old, non-dismissed recommendations before inserting fresh ones
        m.UserRecommendation.objects.filter(
            user=self.user, is_dismissed=False
        ).delete()
 
        topic_map = {
            t.slug: t
            for t in m.Topic.objects.filter(
                slug__in=[r.topic_slug for r in recs if r.topic_slug]
            )
        }
        bulk = []
        for rec in recs:
            bulk.append(m.UserRecommendation(
                user        = self.user,
                topic       = topic_map.get(rec.topic_slug),
                rec_type    = rec.rec_type,
                title       = rec.title,
                description = rec.description,
                url         = rec.url,
                priority    = rec.priority,
            ))
        m.UserRecommendation.objects.bulk_create(bulk)
 