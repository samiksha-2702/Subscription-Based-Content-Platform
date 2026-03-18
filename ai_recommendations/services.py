from app1.models import TestResult
from .models import Topic, UserWeakArea, UserRecommendation


def update_weak_areas(user):
    """
    Analyze test results and calculate weakness score
    """

    results = TestResult.objects.filter(user=user)

    for result in results:
        topic_name = result.test_name.lower()

        # Try matching topic
        topic = Topic.objects.filter(name__icontains=topic_name).first()
        if not topic:
            continue

        # weakness = inverse of score
        weakness = 1 - (result.score / 100)

        UserWeakArea.objects.update_or_create(
            user=user,
            topic=topic,
            defaults={
                'weakness_score': weakness,
                'reason': f"Low score ({result.score}%) in {result.test_name}"
            }
        )


def generate_recommendations(user):
    """
    Generate recommendations from weak areas
    """

    weak_topics = UserWeakArea.objects.filter(user=user).order_by('-weakness_score')[:5]

    # clear old recommendations (optional but recommended)
    UserRecommendation.objects.filter(user=user).delete()

    for wt in weak_topics:
        UserRecommendation.objects.create(
            user=user,
            topic=wt.topic,
            rec_type='topic',
            title=f"Revise {wt.topic.name}",
            description=f"You are weak in this topic. Practice again.",
            priority=int(wt.weakness_score * 10)
        )