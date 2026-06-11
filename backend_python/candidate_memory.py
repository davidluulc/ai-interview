from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db_models import InterviewRecord
from .routes.history import parse_json


def build_candidate_query(profile: dict[str, Any]) -> str:
    return " ".join(
        [
            str(profile.get("candidateName") or ""),
            str(profile.get("targetRole") or ""),
            str(profile.get("resume") or ""),
            str(profile.get("jd") or ""),
        ]
    ).lower()


def score_record(record: InterviewRecord, query: str) -> int:
    score = 0
    fields = [
        record.candidate_name,
        record.target_role,
        record.application_type,
        record.mode,
        record.profile_json,
        record.answers_json,
        record.report_json,
    ]
    for value in fields:
        text = str(value or "").lower()
        for token in query.split():
            if token and token in text:
                score += 1
    return score


def extract_weak_tags(report: dict[str, Any]) -> list[str]:
    tags: list[str] = []

    def add_tags(value: Any) -> None:
        if isinstance(value, list):
            candidates = value
        elif value in (None, ""):
            candidates = []
        else:
            candidates = [value]
        for item in candidates:
            tag = str(item or "").strip()
            if tag and tag not in tags:
                tags.append(tag)

    for review in report.get("questionReviews") or []:
        if isinstance(review, dict):
            add_tags(review.get("weakTags"))

    training_plan = report.get("trainingPlan") if isinstance(report.get("trainingPlan"), dict) else {}
    for topic in training_plan.get("weakTopics") or []:
        if isinstance(topic, dict):
            add_tags(topic.get("weakTags"))

    return tags


def retrieve_candidate_memory(
    db: Session,
    profile: dict[str, Any],
    limit: int = 3,
    user_id: int | None = None,
    application_profile_id: int | None = None,
    min_profile_records: int = 2,
) -> list[dict[str, Any]]:
    statement = select(InterviewRecord)
    if user_id is not None:
        statement = statement.where(InterviewRecord.user_id == user_id)
    records = db.scalars(statement.order_by(InterviewRecord.created_at.desc()).limit(30)).all()
    query = build_candidate_query(profile)
    profile_records = [
        record for record in records if application_profile_id is not None and record.application_profile_id == application_profile_id
    ]
    global_records = [
        record for record in records if application_profile_id is None or record.application_profile_id != application_profile_id
    ]

    def score_records(candidate_records: list[InterviewRecord], scope: str) -> list[tuple[int, InterviewRecord, str]]:
        scored_records = []
        for record in candidate_records:
            score = score_record(record, query)
            if score > 0 or record.target_role == profile.get("targetRole"):
                scored_records.append((score, record, scope))
        scored_records.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
        return scored_records

    profile_scored = score_records(profile_records, "application_profile")
    global_scored = score_records(global_records, "user_global")

    if application_profile_id is not None:
        selected = profile_scored[:limit]
        if len(selected) < min_profile_records:
            selected.extend(global_scored[: max(0, limit - len(selected))])
    else:
        selected = global_scored[:limit]

    memories = []
    seen_record_ids = set()
    for _, record, scope in selected[:limit]:
        if record.id in seen_record_ids:
            continue
        seen_record_ids.add(record.id)
        score = score_record(record, query)
        report = parse_json(record.report_json, {})
        answers = parse_json(record.answers_json, [])
        memories.append(
            {
                "applicationProfileId": record.application_profile_id,
                "memoryScope": scope,
                "targetRole": record.target_role,
                "score": record.score,
                "matchScore": score,
                "risks": report.get("risks") or [],
                "actions": report.get("actions") or [],
                "weakTags": extract_weak_tags(report),
                "recentStages": [answer.get("stage") for answer in answers[-3:] if answer.get("stage")],
            }
        )
    return memories


def build_candidate_profile(memories: list[dict[str, Any]]) -> dict[str, Any]:
    if not memories:
        return {
            "hasHistory": False,
            "scoreTrend": [],
            "averageScore": 0,
            "latestScore": 0,
            "bestScore": 0,
            "recentRisks": [],
            "frequentRisks": [],
            "frequentActions": [],
            "frequentWeakTags": [],
            "weakStages": [],
            "trainingFocus": [],
        }

    risk_counter: Counter[str] = Counter()
    action_counter: Counter[str] = Counter()
    weak_tag_counter: Counter[str] = Counter()
    stage_counter: Counter[str] = Counter()
    score_trend = []

    for memory in memories:
        score = int(memory.get("score") or 0)
        score_trend.append(score)
        risk_counter.update(memory.get("risks") or [])
        action_counter.update(memory.get("actions") or [])
        weak_tag_counter.update(memory.get("weakTags") or [])
        stage_counter.update(memory.get("recentStages") or [])

    recent_risks = []
    for memory in memories[:3]:
        for risk in memory.get("risks") or []:
            if risk not in recent_risks:
                recent_risks.append(risk)

    frequent_risks = [item for item, _ in risk_counter.most_common(5)]
    frequent_actions = [item for item, _ in action_counter.most_common(5)]
    frequent_weak_tags = [item for item, _ in weak_tag_counter.most_common(5)]
    weak_stages = [item for item, _ in stage_counter.most_common(4)]
    training_focus = frequent_actions[:3] or frequent_risks[:3] or frequent_weak_tags[:3] or weak_stages[:3]

    return {
        "hasHistory": True,
        "scoreTrend": score_trend,
        "averageScore": round(sum(score_trend) / len(score_trend)),
        "latestScore": score_trend[0],
        "bestScore": max(score_trend),
        "recentRisks": recent_risks[:5],
        "frequentRisks": frequent_risks,
        "frequentActions": frequent_actions,
        "frequentWeakTags": frequent_weak_tags,
        "weakStages": weak_stages,
        "trainingFocus": training_focus,
    }


def format_candidate_memory(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return "暂无候选人历史画像。"

    blocks = []
    for memory in memories:
        risks = "；".join(memory.get("risks") or [])
        actions = "；".join(memory.get("actions") or [])
        weak_tags = "；".join(memory.get("weakTags") or [])
        stages = "；".join(memory.get("recentStages") or [])
        blocks.append(
            f"岗位：{memory.get('targetRole') or '未知'}；"
            f"得分：{memory.get('score')}；"
            f"近期环节：{stages or '无'}；"
            f"薄弱标签：{weak_tags or '无'}；"
            f"风险点：{risks or '无'}；"
            f"训练建议：{actions or '无'}"
        )

    return "\n".join(blocks)


def format_candidate_profile(profile: dict[str, Any]) -> str:
    if not profile.get("hasHistory"):
        return "暂无长期训练画像。"

    return (
        f"平均分：{profile.get('averageScore')}；"
        f"最近分数：{profile.get('latestScore')}；"
        f"最高分：{profile.get('bestScore')}；"
        f"分数趋势：{' -> '.join(str(score) for score in profile.get('scoreTrend', [])) or '暂无'}；"
        f"高频薄弱环节：{'；'.join(profile.get('weakStages') or []) or '暂无'}；"
        f"高频薄弱标签：{'；'.join(profile.get('frequentWeakTags') or []) or '暂无'}；"
        f"近期风险：{'；'.join(profile.get('recentRisks') or []) or '暂无'}；"
        f"高频风险：{'；'.join(profile.get('frequentRisks') or []) or '暂无'}；"
        f"训练重点：{'；'.join(profile.get('trainingFocus') or []) or '暂无'}"
    )
