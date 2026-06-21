import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db_models import TrainingTask

ACTIVE_STATUSES = {"todo", "in_progress", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}
VALID_PRACTICE_MODES = {"coach", "interview"}
VALID_PRACTICE_DIFFICULTIES = {"basic", "medium", "hard"}
MASTERY_DELTA = {"不会": -5, "模糊": 8, "完整": 15}


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def clamp_score(value: int) -> int:
    return max(0, min(100, int(value)))


def normalize_priority(value: str) -> str:
    return value if value in VALID_PRIORITIES else "medium"


def normalize_practice_mode(value: str) -> str:
    return value if value in VALID_PRACTICE_MODES else "coach"


def normalize_practice_difficulty(value: str) -> str:
    return value if value in VALID_PRACTICE_DIFFICULTIES else "basic"


def parse_json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def serialize_training_task(task: TrainingTask) -> dict[str, Any]:
    return {
        "id": task.id,
        "applicationProfileId": task.application_profile_id,
        "sourceInterviewRecordId": task.source_interview_record_id,
        "weakTag": task.weak_tag,
        "weakLabel": task.weak_label,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "masteryScore": task.mastery_score,
        "attemptCount": task.attempt_count,
        "lastPracticedAt": task.last_practiced_at.isoformat() if task.last_practiced_at else "",
        "nextReviewAt": task.next_review_at.isoformat() if task.next_review_at else "",
        "metadata": parse_json(task.metadata_json, {}),
        "createdAt": task.created_at.isoformat() if task.created_at else "",
        "updatedAt": task.updated_at.isoformat() if task.updated_at else "",
    }


def find_active_task(
    db: Session,
    *,
    user_id: int,
    weak_tag: str,
    application_profile_id: int | None = None,
) -> TrainingTask | None:
    statement = select(TrainingTask).where(
        TrainingTask.user_id == user_id,
        TrainingTask.weak_tag == weak_tag,
        TrainingTask.status.in_(ACTIVE_STATUSES),
    )
    if application_profile_id is None:
        statement = statement.where(TrainingTask.application_profile_id.is_(None))
    else:
        statement = statement.where(TrainingTask.application_profile_id == application_profile_id)
    return db.scalar(statement.order_by(TrainingTask.updated_at.desc(), TrainingTask.id.desc()))


def create_or_update_training_task(
    db: Session,
    *,
    user_id: int,
    weak_tag: str,
    weak_label: str,
    title: str,
    description: str,
    priority: str = "medium",
    mastery_score: int = 40,
    metadata: dict[str, Any] | None = None,
    application_profile_id: int | None = None,
    source_interview_record_id: int | None = None,
) -> TrainingTask:
    task = find_active_task(
        db,
        user_id=user_id,
        weak_tag=weak_tag,
        application_profile_id=application_profile_id,
    )
    if not task:
        task = TrainingTask(user_id=user_id, weak_tag=weak_tag, application_profile_id=application_profile_id)
        db.add(task)

    task.source_interview_record_id = source_interview_record_id or task.source_interview_record_id
    task.weak_label = weak_label
    task.title = title
    task.description = description
    task.priority = normalize_priority(priority)
    task.mastery_score = clamp_score(mastery_score)
    task.metadata_json = dump_json(metadata or {})
    task.updated_at = utc_now_naive()
    db.commit()
    db.refresh(task)
    return task


def get_owned_training_task(db: Session, task_id: int, *, user_id: int) -> TrainingTask:
    task = db.scalar(select(TrainingTask).where(TrainingTask.id == task_id, TrainingTask.user_id == user_id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training task not found")
    return task


def _safe_template_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _build_practice_rubric(answer_key_points: list[str]) -> list[str]:
    if not answer_key_points:
        return ["是否讲清背景", "是否结合项目做法", "是否说明结果和复盘"]
    return [f"是否覆盖：{point}" for point in answer_key_points[:4]]


def _normalize_answer_text(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def build_practice_feedback(task: TrainingTask, answer_text: str) -> dict[str, Any]:
    from .weakness_training_templates import get_training_template

    template = get_training_template(task.weak_tag)
    answer_key_points = _safe_template_list(template.get("answerKeyPoints"))[:8]
    normalized_answer = _normalize_answer_text(answer_text)
    covered = [point for point in answer_key_points if point.lower() in normalized_answer]
    missing = [point for point in answer_key_points if point not in covered]
    if not normalized_answer:
        correction_tips = ["先写出自己的理解，再按回答要点逐条补齐。"]
    else:
        correction_tips = [f"建议补充：{point}" for point in missing[:3]]
    coverage_ratio = len(covered) / len(answer_key_points) if answer_key_points else 0
    if coverage_ratio >= 0.75:
        quality_label = "覆盖较完整"
        next_action = "把回答压缩成 1 分钟版本，并补一个项目验证细节。"
    elif coverage_ratio >= 0.35:
        quality_label = "部分覆盖"
        next_action = "优先补齐缺失要点，再用一个项目例子串起来。"
    else:
        quality_label = "覆盖不足"
        next_action = "先对照回答要点重写一版，再提交练习。"
    return {
        "qualityLabel": quality_label,
        "coveredKeyPoints": covered,
        "missingKeyPoints": missing,
        "correctionTips": correction_tips,
        "nextAction": next_action,
    }


def build_practice_review(task: TrainingTask, answer_text: str) -> dict[str, Any]:
    from .weakness_training_templates import get_training_template

    template = get_training_template(task.weak_tag)
    answer_key_points = _safe_template_list(template.get("answerKeyPoints"))[:8]
    common_mistakes = _safe_template_list(template.get("commonMistakes"))[:4]
    feedback = build_practice_feedback(task, answer_text)
    covered = feedback["coveredKeyPoints"]
    missing = feedback["missingKeyPoints"]
    score = int(round((len(covered) / len(answer_key_points)) * 100)) if answer_key_points else 0
    reference_answer = (
        f"这道题可以按这些要点回答：{'、'.join(answer_key_points)}。"
        if answer_key_points
        else "这道题建议按背景、职责、做法、结果和复盘来回答。"
    )
    issues = [f"缺少关键点：{point}" for point in missing[:5]]
    if not str(answer_text or "").strip():
        issues.insert(0, "当前回答为空，需要先写出自己的理解。")
    for mistake in common_mistakes:
        if mistake and mistake not in issues:
            issues.append(f"注意避免：{mistake}")
    rewritten_answer = (
        f"建议改写为：{reference_answer} 结合你的项目时，补充具体场景、实现方式和验证结果。"
    )
    next_practice = (
        "先对照参考答案补齐缺失点，再用自己的项目经历复述一遍。"
        if missing
        else "下一步把答案压缩到 1 分钟，并加入一个真实项目细节。"
    )
    return {
        "score": score,
        "qualityLabel": feedback["qualityLabel"],
        "referenceAnswer": reference_answer,
        "strengths": [f"已覆盖：{point}" for point in covered],
        "issues": issues,
        "missingKeyPoints": missing,
        "rewrittenAnswer": rewritten_answer,
        "nextPractice": next_practice,
    }


def practice_submission_fingerprint(answer_status: str, answer_text: str, self_rating: int | None) -> str:
    return dump_json(
        {
            "answerStatus": str(answer_status or ""),
            "answerText": _normalize_answer_text(answer_text),
            "selfRating": self_rating,
        }
    )


def build_training_practice_payload(
    task: TrainingTask,
    *,
    mode: str = "coach",
    difficulty: str = "basic",
) -> dict[str, Any]:
    from .weakness_training_templates import get_training_template

    normalized_mode = normalize_practice_mode(mode)
    normalized_difficulty = normalize_practice_difficulty(difficulty)
    template = get_training_template(task.weak_tag)
    ladder = template.get("difficultyLadder") if isinstance(template.get("difficultyLadder"), dict) else {}
    ladder_questions = _safe_template_list(ladder.get(normalized_difficulty)) or _safe_template_list(
        ladder.get("basic")
    )
    mode_key = "coachQuestions" if normalized_mode == "coach" else "interviewQuestions"
    mode_questions = _safe_template_list(template.get(mode_key))
    question = (
        ladder_questions
        or mode_questions
        or _safe_template_list(template.get("coachQuestions"))
        or ["请结合项目讲清这个薄弱点。"]
    )[0]
    answer_key_points = _safe_template_list(template.get("answerKeyPoints"))[:8]
    common_mistakes = _safe_template_list(template.get("commonMistakes"))[:6]
    return {
        "weakTag": task.weak_tag,
        "weakLabel": task.weak_label or str(template.get("label") or task.weak_tag),
        "mode": normalized_mode,
        "difficulty": normalized_difficulty,
        "question": question,
        "answerKeyPoints": answer_key_points,
        "commonMistakes": common_mistakes,
        "oneMinuteTemplate": str(template.get("oneMinuteTemplate") or ""),
        "relatedTags": _safe_template_list(template.get("relatedTags"))[:6],
        "rubric": _build_practice_rubric(answer_key_points),
        "fallbackUsed": bool(template.get("fallbackUsed")),
    }


def complete_training_task(
    db: Session,
    task_id: int,
    *,
    user_id: int,
    answer_status: str,
    answer_text: str = "",
    self_rating: int | None = None,
) -> TrainingTask:
    task = get_owned_training_task(db, task_id, user_id=user_id)
    metadata = parse_json(task.metadata_json, {})
    fingerprint = practice_submission_fingerprint(answer_status, answer_text, self_rating)
    last_practice = metadata.get("lastPractice") if isinstance(metadata.get("lastPractice"), dict) else {}
    if last_practice.get("submissionFingerprint") == fingerprint:
        last_practice["duplicateSubmission"] = True
        metadata["lastPractice"] = last_practice
        task.metadata_json = dump_json(metadata)
        task.updated_at = utc_now_naive()
        db.commit()
        db.refresh(task)
        return task

    delta = MASTERY_DELTA.get(answer_status, 0)
    task.mastery_score = clamp_score(task.mastery_score + delta)
    task.attempt_count += 1
    task.last_practiced_at = utc_now_naive()
    task.updated_at = utc_now_naive()
    task.status = "done" if task.mastery_score >= 80 else "in_progress"
    metadata["lastPractice"] = {
        "answerStatus": answer_status,
        "answerPreview": str(answer_text or "")[:300],
        "selfRating": self_rating,
        "feedback": build_practice_feedback(task, answer_text),
        "review": build_practice_review(task, answer_text),
        "submissionFingerprint": fingerprint,
        "duplicateSubmission": False,
        "completedAt": task.last_practiced_at.isoformat() if task.last_practiced_at else "",
    }
    task.metadata_json = dump_json(metadata)
    db.commit()
    db.refresh(task)
    return task


def list_candidate_training_tasks(
    db: Session,
    *,
    user_id: int,
    application_profile_id: int | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    statement = select(TrainingTask).where(
        TrainingTask.user_id == user_id,
        TrainingTask.status.in_(("todo", "in_progress")),
    )
    tasks = db.scalars(statement).all()
    if application_profile_id is not None:
        tasks = [
            task
            for task in tasks
            if task.application_profile_id in (None, application_profile_id)
        ]

    priority_rank = {"high": 0, "medium": 1, "low": 2}
    tasks.sort(
        key=lambda task: (
            priority_rank.get(task.priority, 1),
            task.mastery_score,
            -(task.updated_at.timestamp() if task.updated_at else 0),
            -task.id,
        )
    )
    return [serialize_training_task(task) for task in tasks[: max(1, limit)]]


def select_agent_training_task(tasks: list[dict[str, Any]], *, agent_mode: str) -> dict[str, Any]:
    for task in tasks:
        mastery_score = int(task.get("masteryScore") or 0)
        priority = str(task.get("priority") or "medium")
        if agent_mode == "coach" and priority == "high" and mastery_score < 60:
            return {
                **task,
                "reason": "训练任务显示该薄弱点优先级高且掌握度偏低，coach 模式先拆小训练。",
            }
        if agent_mode == "interview" and mastery_score < 80:
            return {
                **task,
                "reason": "训练任务显示该薄弱点尚未稳定掌握，interview 模式可作为追问参考。",
            }
    return {}
