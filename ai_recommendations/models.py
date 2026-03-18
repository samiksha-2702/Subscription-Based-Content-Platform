from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
 
 
# ─────────────────────────────────────────────
# 1. TOPIC REGISTRY
# ─────────────────────────────────────────────
 
class Topic(models.Model):
    """
    Central registry of every learnable topic in PrepEdge.
    Covers Programming, SQL, DSA, and Communication modules.
    """
 
    MODULE_CHOICES = [
        ('python',          'Python'),
        ('java',            'Java'),
        ('cpp',             'C++'),
        ('javascript',      'JavaScript'),
        ('sql',             'SQL / Databases'),
        ('dsa',             'Data Structures & Algorithms'),
        ('communication',   'Communication'),
        ('soft_skills',     'Soft Skills'),
    ]
 
    DIFFICULTY_CHOICES = [
        ('beginner',        'Beginner'),
        ('intermediate',    'Intermediate'),
        ('advanced',        'Advanced'),
    ]
 
    name        = models.CharField(max_length=200)
    slug        = models.SlugField(unique=True)           # e.g. "python-oop"
    module      = models.CharField(max_length=50, choices=MODULE_CHOICES)
    difficulty  = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    description = models.TextField(blank=True)
 
    # Prerequisite topics (graph edge for learning path)
    prerequisites = models.ManyToManyField(
        'self', symmetrical=False, blank=True,
        related_name='unlocks'
    )
 
    # Rich metadata used by the recommender
    keywords    = models.JSONField(default=list, blank=True)   # ["loops","iteration","range"]
    resource_url = models.URLField(blank=True)                 # link inside PrepEdge
 
    class Meta:
        ordering = ['module', 'name']
 
    def __str__(self):
        return f"[{self.get_module_display()}] {self.name}"
 
 
# ─────────────────────────────────────────────
# 2. USER PERFORMANCE TRACKING
# ─────────────────────────────────────────────
 
class UserQuizAttempt(models.Model):
    """
    Records every quiz / test attempt a user makes.
    One row per attempt (users can retry).
    """
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    topic       = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='quiz_attempts')
 
    score       = models.FloatField()          # percentage 0-100
    max_score   = models.FloatField(default=100)
    time_taken  = models.DurationField(null=True, blank=True)  # how long they took
    attempted_at = models.DateTimeField(default=timezone.now)
 
    # Granular wrong-answer tracking (list of question IDs or topic slugs)
    wrong_topics = models.JSONField(default=list, blank=True)
 
    class Meta:
        ordering = ['-attempted_at']
 
    def __str__(self):
        return f"{self.user.username} | {self.topic.name} | {self.score:.1f}%"
 
    @property
    def passed(self):
        return self.score >= 60.0
 
 
class UserPracticeCompletion(models.Model):
    """
    Tracks completion of practice exercises per topic.
    """
    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='practice_completions')
    topic           = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='practice_completions')
    completed_at    = models.DateTimeField(default=timezone.now)
    exercise_count  = models.PositiveIntegerField(default=1)   # how many exercises done
 
    class Meta:
        unique_together = ('user', 'topic')   # one progress record per user-topic pair
        ordering = ['-completed_at']
 
    def __str__(self):
        return f"{self.user.username} completed {self.topic.name}"
 
 
class UserWeakArea(models.Model):
    """
    Computed / updated automatically by the recommender engine.
    Stores the current weakness score per topic for each user.
    weakness_score: 0.0 (strong) → 1.0 (very weak)
    """
    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weak_areas')
    topic           = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='weak_areas')
    weakness_score  = models.FloatField(default=0.5)   # computed; higher = weaker
    last_updated    = models.DateTimeField(auto_now=True)
    reason          = models.CharField(max_length=200, blank=True)  # human-readable reason
 
    class Meta:
        unique_together = ('user', 'topic')
        ordering = ['-weakness_score']
 
    def __str__(self):
        return f"{self.user.username} | {self.topic.name} | weakness={self.weakness_score:.2f}"
 
 
class UserRecommendation(models.Model):
    """
    Stores AI-generated recommendations for a user.
    Regenerated periodically or on-demand.
    """
    RECOMMENDATION_TYPES = [
        ('topic',       'Revisit Topic'),
        ('exercise',    'Practice Exercise'),
        ('article',     'Read Article'),
        ('path',        'Learning Path'),
        ('tip',         'AI Tip'),
    ]
 
    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    topic           = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True)
    rec_type        = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    title           = models.CharField(max_length=300)
    description     = models.TextField()
    url             = models.CharField(max_length=500, blank=True)  # internal URL
    priority        = models.PositiveSmallIntegerField(default=5)   # 1=highest
    is_dismissed    = models.BooleanField(default=False)
    created_at      = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['priority', '-created_at']
 
    def __str__(self):
        return f"[{self.rec_type}] {self.user.username} → {self.title}"