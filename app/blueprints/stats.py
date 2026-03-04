import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Question, Topic, WrongAnswer

stats_bp = Blueprint("stats", __name__)


def _to_tokens(tags):
    if tags is None:
        return []

    if isinstance(tags, list):
        return [str(x).strip() for x in tags if str(x).strip()]

    if isinstance(tags, dict):
        tokens = []
        for k, v in tags.items():
            if str(k).strip():
                tokens.append(str(k).strip())
            if isinstance(v, str) and v.strip():
                tokens.append(v.strip())
        return tokens

    if isinstance(tags, str):
        raw = tags.strip()
        if not raw:
            return []

        if raw.startswith("[") or raw.startswith("{"):
            try:
                parsed = json.loads(raw)
                return _to_tokens(parsed)
            except json.JSONDecodeError:
                pass

        split_tokens = re.split(r"[,\s]+", raw)
        return [x.strip() for x in split_tokens if x.strip()]

    return [str(tags).strip()] if str(tags).strip() else []


def resolve_topic_for_question(tags, topics):
    tokens = _to_tokens(tags)
    if not tokens:
        return "기타/미분류"

    token_norm_map = {t: t.lower() for t in tokens if t}

    for topic in topics:
        topic_norm = topic.name.lower()
        for raw, norm in token_norm_map.items():
            if norm == topic_norm:
                return topic.name

    best_name = None
    best_len = 0
    for topic in topics:
        topic_norm = topic.name.lower()
        for _raw, norm in token_norm_map.items():
            if topic_norm in norm or norm in topic_norm:
                matched_len = min(len(topic_norm), len(norm))
                if matched_len > best_len:
                    best_len = matched_len
                    best_name = topic.name

    return best_name or "기타/미분류"


@stats_bp.route("/")
@login_required
def index():
    recent_days = request.args.get("recent_days", "all")

    query = db.session.query(WrongAnswer, Question).join(
        Question, WrongAnswer.question_id == Question.id
    ).filter(
        WrongAnswer.user_id == current_user.id,
        WrongAnswer.mastered.is_(False),
    )

    if recent_days == "7":
        cutoff = datetime.utcnow() - timedelta(days=7)
        query = query.filter(WrongAnswer.last_wrong_at >= cutoff)

    rows = query.all()
    topics = Topic.query.order_by(Topic.name.asc()).all()

    counter = defaultdict(int)
    for topic in topics:
        counter[topic.name] += 0
    counter["기타/미분류"] += 0

    for wrong, question in rows:
        topic_name = resolve_topic_for_question(question.tags, topics)
        counter[topic_name] += 1

    labels = sorted(counter.keys())
    counts = [counter[name] for name in labels]
    total = sum(counts)
    percentages = [round((c / total) * 100, 2) if total > 0 else 0 for c in counts]

    rows_for_table = [
        {
            "topic": topic,
            "count": counter[topic],
            "percent": round((counter[topic] / total) * 100, 2) if total > 0 else 0,
        }
        for topic in sorted(counter.keys(), key=lambda x: counter[x], reverse=True)
    ]

    return render_template(
        "stats/index.html",
        labels=labels,
        counts=counts,
        percentages=percentages,
        total=total,
        table_rows=rows_for_table,
        recent_days=recent_days,
    )
