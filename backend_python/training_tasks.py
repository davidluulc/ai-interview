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
REFERENCE_ANSWER_BY_TAG = {
    "rag_quality": (
        "可以这样回答：我会把 RAG 质量拆成召回是否命中、排序是否合理、资料是否可解释三层来看。"
        "Hit@K 用来判断正确资料是否出现在前 K 条结果里，MRR 更关注正确资料排在多靠前；关键词覆盖率可以辅助判断问题里的核心词是否被召回；"
        "空召回率能发现知识库缺资料、embedding 维度不一致或 metadata 过滤过严的问题；metadata 匹配率和命中日志则用来追踪这次回答到底用了哪类知识库、哪些 chunk、分数如何。"
        "线上排查时，我会先看命中日志和空召回，再结合 Hit@K/MRR 判断是检索问题、排序问题，还是最终生成问题。"
    ),
    "rag_retrieval": (
        "可以这样回答：一次 RAG 检索通常先根据用户问题构造 query，再在合适的知识库和 metadata 范围内查找资料。"
        "chunk 切分决定资料颗粒度，BM25 更适合命中关键词和专有名词，向量检索更适合理解语义相近的问题；hybrid search 会融合两类结果，"
        "rerank 再把更贴近问题的 chunk 排到前面。实际项目里还需要记录 query、metadata filter、召回来源、分数和最终 top chunks，方便定位是 query 构造、过滤条件、向量模型还是重排阶段出了问题。"
    ),
    "agent_state": (
        "可以这样回答：Agent State 是当前面试局面的结构化快照，里面会放轮次、历史问答、候选人画像命中、RAG 召回摘要、薄弱点策略和剩余轮数等信息。"
        "ToolCalls 记录系统为了决策调用了哪些检索或分析工具，Agent Decision 表示下一步要追问、降难度、换方向还是结束复盘。"
        "模型输出不稳定时，fallback、normalize 和 guardrail 会把非法决策兜底成可执行动作；nodeTrace 用来记录每个节点的输入输出，方便在后台复盘为什么生成了这道题。"
    ),
    "backend_fastapi": (
        "可以这样回答：router 负责声明接口路径、请求方法和依赖注入，是请求进入 FastAPI 后端的入口；"
        "schema 负责用 Pydantic 定义请求体、响应体和字段校验，避免前后端 payload 对不上；"
        "db_model 用 SQLAlchemy 描述数据库表、字段和关系；database 负责创建 engine、SessionLocal，并通过 get_db 把数据库会话注入到接口里。"
        "一次请求通常会经过 router 参数解析、schema 校验、Depends 注入数据库会话和当前用户、业务逻辑处理、数据库读写，最后按响应 schema 返回；鉴权和错误处理则保证接口不会越权，也能把异常转成前端可理解的响应。"
    ),
    "database_modeling": (
        "可以这样回答：数据库建模先要明确每张表保存什么业务对象，再用主键标识单条记录、外键表达对象之间的归属关系。"
        "在这个项目里，user_id 是隔离多用户数据的关键字段，面试记录、投递档案、RAG 文档和 Agent 日志都应该能追溯到所属用户或所属面试。"
        "SQLAlchemy 的 relationship 方便代码层按对象关系访问数据，但真正的数据安全还要靠查询时按 user_id 过滤。"
        "如果从 SQLite 迁到 PostgreSQL，Alembic 迁移负责让表结构可重复、可追踪地演进。"
    ),
    "project_storytelling": (
        "可以这样回答：这个项目面向准备面试但缺少针对性练习的人，核心流程是先维护简历、JD 和项目知识库，再由系统生成贴合岗位的模拟面试问题。"
        "回答过程中，系统会结合候选人画像、岗位知识库和题库做 RAG 召回，再通过 Agent 决策控制追问、降难度或进入复盘。"
        "工程上我重点做了前后端闭环、PostgreSQL/Redis/Celery 的生产化部署、AI 请求和 RAG trace 的可观测性，以及面试报告和训练任务沉淀。"
        "这样讲能体现业务目标、技术方案、工程难点和上线验证，而不是只背技术栈。"
    ),
}


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


def build_reference_answer(weak_tag: str, answer_key_points: list[str]) -> str:
    reference_answer = REFERENCE_ANSWER_BY_TAG.get(str(weak_tag or "").strip())
    if reference_answer:
        return reference_answer
    if not answer_key_points:
        return "可以这样回答：先说明问题背景，再讲自己承担的职责和具体做法，最后补充结果、验证方式和复盘改进。"
    key_point_text = "、".join(answer_key_points[:6])
    return (
        f"可以这样回答：这道题至少要覆盖 {key_point_text}。"
        "回答时不要只罗列名词，先解释每个关键点解决什么问题，再结合你的项目说明具体实现方式、排查过程和结果验证。"
    )


def build_practice_review(task: TrainingTask, answer_text: str) -> dict[str, Any]:
    from .weakness_training_templates import get_training_template

    template = get_training_template(task.weak_tag)
    answer_key_points = _safe_template_list(template.get("answerKeyPoints"))[:8]
    common_mistakes = _safe_template_list(template.get("commonMistakes"))[:4]
    feedback = build_practice_feedback(task, answer_text)
    covered = feedback["coveredKeyPoints"]
    missing = feedback["missingKeyPoints"]
    score = int(round((len(covered) / len(answer_key_points)) * 100)) if answer_key_points else 0
    reference_answer = build_reference_answer(task.weak_tag, answer_key_points)
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
