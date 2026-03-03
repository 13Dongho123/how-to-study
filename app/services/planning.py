from datetime import date, timedelta

from app.models import StudyPlan


def generate_study_plans(exam, topics):
    today = date.today()
    if exam.exam_date < today:
        raise ValueError("시험일은 오늘 이후여야 합니다.")

    excluded = set(exam.excluded_weekdays or [])

    weighted_topics = []
    for topic in topics:
        weighted_topics.extend([topic] * max(1, int(topic.weight)))
    if not weighted_topics:
        return []

    plans = []
    cursor = today
    idx = 0
    while cursor <= exam.exam_date:
        weekday = cursor.weekday()  # Monday=0
        if weekday not in excluded:
            is_weekend = weekday in (5, 6)
            minutes = exam.weekend_minutes if is_weekend else exam.daily_minutes
            topic = weighted_topics[idx % len(weighted_topics)]
            week_no = ((cursor - today).days // 7) + 1
            plans.append(
                StudyPlan(
                    user_id=exam.user_id,
                    exam_id=exam.id,
                    plan_date=cursor,
                    week_no=week_no,
                    topic_id=topic.id,
                    minutes=minutes,
                    note=f"{topic.name} 중심 학습",
                )
            )
            idx += 1
        cursor += timedelta(days=1)

    return plans
