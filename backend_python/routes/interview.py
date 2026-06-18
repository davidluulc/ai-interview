import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..agent_logging import create_agent_decision_log
from ..agent_orchestrator import run_next_question_agent
from ..agent_runtime import run_agent_runtime
from ..agent_trace import build_node_trace
from ..auth import get_current_user
from ..candidate_memory import (
    build_candidate_profile,
    format_candidate_memory,
    format_candidate_profile,
    retrieve_candidate_memory,
)
from ..database import get_db
from ..db_models import User
from ..interview_agent import build_debug_signals
from ..langgraph_agent.adapters import decide_real_action_for_graph, retrieve_real_context_for_graph
from ..langgraph_agent.checkpoint_store import checkpoint_summary_store
from ..langgraph_agent.checkpoint_persistence import save_checkpoint_summary
from ..langgraph_agent.service import run_langgraph_agent_v2
from ..llm_client import call_model
from ..prompts.interview import NEXT_QUESTION_SYSTEM_PROMPT, REPORT_SYSTEM_PROMPT, build_context_message
from ..question_rag import format_question_context, retrieve_questions
from ..rag import format_role_context, retrieve_role_context
from ..rag_explain import build_user_rag_reason
from ..rag_logging import build_rag_query, create_rag_log, infer_retrieval_mode
from ..rag_quality import evaluate_retrieval_quality
from ..runtime_audit import build_runtime_audit
from ..runtime_policy import decide_runtime_policy
from ..schemas import QuestionRequest, QuestionResponse, ReportRequest, ReportResponse
from ..security import client_identity, enforce_rate_limit
from ..training_tags import merge_weak_tags
from ..training_tasks import list_candidate_training_tasks, select_agent_training_task

router = APIRouter(prefix="/api/interview", tags=["interview"])


def log_retrievals(
    db: Session,
    *,
    current_user: User,
    application_profile_id: int | None,
    request_type: str,
    query_text: str,
    role_hits: list[dict[str, Any]],
    question_hits: list[dict[str, Any]],
    memory_hits: list[dict[str, Any]],
) -> None:
    for retriever_name, hits in [
        ("role_knowledge", role_hits),
        ("question_bank", question_hits),
        ("candidate_memory", memory_hits),
    ]:
        create_rag_log(
            db,
            user_id=current_user.id,
            application_profile_id=application_profile_id,
            request_type=request_type,
            query_text=query_text,
            retriever_name=retriever_name,
            hits=hits,
            retrieval_mode=infer_retrieval_mode(hits),
            used_in_prompt=True,
        )


def append_generate_question_trace(
    *,
    agent_state: dict[str, Any],
    agent_decision: dict[str, Any],
    normalized_question: dict[str, Any],
    role_hits: list[dict[str, Any]],
    question_hits: list[dict[str, Any]],
    memory_hits: list[dict[str, Any]],
) -> None:
    node_trace = list(agent_decision.get("nodeTrace") or agent_state.get("nodeTrace") or [])
    generate_trace = build_node_trace(
        node_name="generate_question",
        input_summary={
            "decisionAction": agent_decision.get("nextAction"),
            "decisionFocus": agent_decision.get("focus"),
            "decisionDifficulty": agent_decision.get("difficulty"),
            "roleHitCount": len(role_hits),
            "questionHitCount": len(question_hits),
            "memoryHitCount": len(memory_hits),
        },
        output_summary={
            "stage": normalized_question.get("stage"),
            "focus": normalized_question.get("focus"),
            "stability": normalized_question.get("stability"),
            "promptLength": len(str(normalized_question.get("prompt") or "")),
        },
        fallback_used=bool(agent_decision.get("guardrailApplied")),
    )
    node_trace.append(generate_trace)
    agent_state["nodeTrace"] = node_trace
    agent_decision["nodeTrace"] = node_trace


def append_update_memory_trace(
    *,
    agent_state: dict[str, Any],
    agent_decision: dict[str, Any],
    normalized_question: dict[str, Any],
) -> None:
    node_trace = list(agent_decision.get("nodeTrace") or agent_state.get("nodeTrace") or [])
    should_update_memory = bool(agent_decision.get("shouldUpdateMemory"))
    update_trace = build_node_trace(
        node_name="update_memory",
        input_summary={
            "shouldUpdateMemory": should_update_memory,
            "focus": normalized_question.get("focus"),
            "stage": normalized_question.get("stage"),
        },
        output_summary={
            "shouldUpdateMemory": should_update_memory,
            "status": "deferred",
            "reason": "next_question 阶段只记录候选人画像更新意图，长期训练画像在报告或历史保存链路中沉淀。",
        },
    )
    node_trace.append(update_trace)
    agent_state["nodeTrace"] = node_trace
    agent_decision["nodeTrace"] = node_trace


def build_mode_guidance(agent_mode: str) -> dict[str, str]:
    if agent_mode == "coach":
        return {
            "mode": "coach",
            "style": "学习辅导模式：把问题拆小，先确认基础概念，再逐步引导到项目表达。",
            "weakAnswerGuidance": "如果上一轮回答不会或很短，先给回答框架提示，再问一个更小的问题。",
        }
    return {
        "mode": "interview",
        "style": "真实面试模式：保持必要压力，追问实现细节、技术取舍和真实性，但不能羞辱候选人。",
        "weakAnswerGuidance": "如果候选人连续答不上来，先追问基础概念；仍然不会时切换到相邻话题，避免无效重复。",
    }


def build_question_strategy_payload(
    *,
    history: list[dict[str, Any]],
    role_hits: list[dict[str, Any]],
    question_hits: list[dict[str, Any]],
    memory_hits: list[dict[str, Any]],
    agent_mode: str = "interview",
    agent_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    last_answer = history[-1] if history else {}
    weakness_strategy = (
        agent_decision.get("weaknessStrategy")
        if isinstance(agent_decision, dict) and isinstance(agent_decision.get("weaknessStrategy"), dict)
        else {}
    )
    training_template_hint = (
        agent_decision.get("trainingTemplateHint")
        if isinstance(agent_decision, dict) and isinstance(agent_decision.get("trainingTemplateHint"), dict)
        else {}
    )
    answer_key_points = (
        training_template_hint.get("answerKeyPoints") if isinstance(training_template_hint.get("answerKeyPoints"), list) else []
    )
    common_mistakes = (
        training_template_hint.get("commonMistakes") if isinstance(training_template_hint.get("commonMistakes"), list) else []
    )
    return {
        "lastAnswer": last_answer,
        "askedQuestions": [str(item.get("question") or "") for item in history if item.get("question")],
        "retrievalQuality": {
            "roleKnowledge": evaluate_retrieval_quality(role_hits),
            "questionBank": evaluate_retrieval_quality(question_hits),
            "candidateMemory": evaluate_retrieval_quality(memory_hits),
        },
        "questionStrategy": {
            "avoidRepeat": True,
            "followLastAnswer": True,
            "oneQuestionOnly": True,
            "modeGuidance": build_mode_guidance(agent_mode),
            "ragGuidance": "优先围绕命中良好的 RAG 资料和上一轮回答继续追问；不要重复 askedQuestions 中已经问过的问题。",
            "weaknessStrategy": {
                "enabled": bool(weakness_strategy.get("enabled")),
                "primaryWeakTag": str(weakness_strategy.get("primaryWeakTag") or ""),
                "primaryWeakLabel": str(weakness_strategy.get("primaryWeakLabel") or ""),
                "modePolicy": str(weakness_strategy.get("modePolicy") or "none"),
                "reason": str(weakness_strategy.get("reason") or ""),
            },
            "trainingTemplateHint": {
                "enabled": bool(training_template_hint.get("enabled")),
                "weakTag": str(training_template_hint.get("weakTag") or ""),
                "label": str(training_template_hint.get("label") or ""),
                "mode": str(training_template_hint.get("mode") or agent_mode),
                "difficulty": str(training_template_hint.get("difficulty") or ""),
                "recommendedQuestion": str(training_template_hint.get("recommendedQuestion") or ""),
                "answerKeyPoints": [str(item) for item in answer_key_points[:6]],
                "commonMistakes": [str(item) for item in common_mistakes[:4]],
                "oneMinuteTemplate": str(training_template_hint.get("oneMinuteTemplate") or ""),
            },
        },
    }


WEAK_ANSWER_MARKERS = ("不会", "不知道", "写不出来", "不清楚", "不了解", "没接触")
ALLOWED_ANSWER_STATUSES = {"完整", "模糊", "不会", "跑题"}
GENERIC_FOCUS_TITLES = {
    "自我介绍",
    "项目背景",
    "项目职责",
    "技术基础",
    "技术追问",
    "场景问题",
    "行为面试",
    "薪资与规划",
    "动态追问",
    "综合追问",
}
FOCUS_RULES = [
    ("RAG 召回链路", ("rag", "召回", "检索", "重排", "chunk", "切片", "知识库", "命中日志", "hits_json", "quality")),
    ("后端模块设计", ("fastapi", "接口", "路由", "后端", "模块", "sqlalchemy", "schema")),
    ("项目经历核验", ("简历", "真实性", "经历", "负责", "项目")),
    ("部署上线理解", ("部署", "docker", "nginx", "云服务器", "上线")),
    ("数据库与缓存", ("redis", "mysql", "数据库", "事务", "缓存", "索引")),
    ("求职规划表达", ("薪资", "到岗", "规划", "期望", "反问")),
]

FOCUS_FALLBACK_ORDER = [
    "后端模块设计",
    "RAG 召回链路",
    "数据库与缓存",
    "项目经历核验",
    "部署上线理解",
    "求职规划表达",
]


def classify_answer_status(answer_text: str) -> str:
    normalized = (answer_text or "").strip()
    if not normalized:
        return "不会"
    if any(marker in normalized for marker in WEAK_ANSWER_MARKERS):
        return "不会"
    if len(normalized) < 24:
        return "模糊"
    return "完整"


def infer_question_focus(*parts: str, fallback: str = "综合追问") -> str:
    text = " ".join(str(part or "") for part in parts).lower()
    for focus, keywords in FOCUS_RULES:
        if any(keyword in text for keyword in keywords):
            return focus
    return fallback


def normalize_next_question_focus(result: dict[str, Any], agent_decision: dict[str, Any], profile: dict[str, Any]) -> str:
    raw_focus = str(result.get("focus") or "").strip()
    if raw_focus and raw_focus not in GENERIC_FOCUS_TITLES:
        return raw_focus[:16]
    inferred = infer_question_focus(
        str(result.get("prompt") or ""),
        str(agent_decision.get("focus") or ""),
        str(profile.get("resume") or ""),
        str(profile.get("jd") or ""),
        fallback=str(agent_decision.get("focus") or raw_focus or "综合追问"),
    )
    return inferred[:16]


def is_hard_prompt_for_weak_answer(prompt: str) -> bool:
    text = str(prompt or "")
    hard_markers = ("完整", "必须", "现场写出", "给出公式", "写代码", "json.loads")
    hard_targets = ("JSON", "json", "公式", "代码", "hits_json", "quality")
    return any(marker in text for marker in hard_markers) and any(target in text for target in hard_targets)


def soften_prompt_for_weak_answer(prompt: str, focus: str, agent_decision: dict[str, Any]) -> str:
    action = str(agent_decision.get("nextAction") or "")
    mode = str(agent_decision.get("agentMode") or "")
    if action != "lower_difficulty" and mode != "coach":
        return prompt
    if not is_hard_prompt_for_weak_answer(prompt):
        return prompt
    if "RAG" in focus:
        return (
            "我们先拆小一点：RAG 命中日志通常要记录 query_text、retriever_name、hit_count "
            "和 hits_json。你先不用写完整 JSON，先说说 query_text 和 hits_json 分别表示什么？"
        )
    return f"我们先拆小一点：围绕「{focus}」，你先说一个最基础的概念和一个项目里的使用场景。"


def normalize_text_for_compare(text: str) -> str:
    return re.sub(r"[\W_]+", "", str(text or "").lower(), flags=re.UNICODE)


def is_repeated_prompt(prompt: str, history: list[dict[str, Any]]) -> bool:
    normalized_prompt = normalize_text_for_compare(prompt)
    if not normalized_prompt:
        return False
    for item in history:
        asked = normalize_text_for_compare(str(item.get("question") or ""))
        if asked and (asked == normalized_prompt or asked in normalized_prompt or normalized_prompt in asked):
            return True
    return False


def select_alternative_focus(current_focus: str, profile: dict[str, Any]) -> str:
    profile_text = " ".join(str(profile.get(key) or "") for key in ("targetRole", "resume", "jd", "companyNeeds"))
    for focus, keywords in FOCUS_RULES:
        if focus == current_focus:
            continue
        if any(keyword in profile_text.lower() for keyword in keywords):
            return focus
    for focus in FOCUS_FALLBACK_ORDER:
        if focus != current_focus:
            return focus
    return "综合追问"


def build_switch_focus_prompt(focus: str, agent_mode: str) -> str:
    if agent_mode == "coach":
        return f"换个角度，我们先不继续卡在上一题。围绕「{focus}」，你先用自己的话说一个基础概念，再补一个你项目里可能用到它的场景。"
    return f"换个角度继续考察。围绕「{focus}」，请结合你的项目说明一个实现细节，并说清楚你为什么这样设计。"


def record_repeated_prompt_guardrail(agent_decision: dict[str, Any], focus: str) -> None:
    trigger_rules = agent_decision.get("triggerRules") if isinstance(agent_decision.get("triggerRules"), list) else []
    if "repeated_prompt_guardrail" not in trigger_rules:
        trigger_rules = [*trigger_rules, "repeated_prompt_guardrail"]
    reason = "检测到模型生成了重复问题，后端已切换到相邻考察点。"
    previous_focus = str(agent_decision.get("focus") or "").strip()
    agent_decision["triggerRules"] = trigger_rules
    agent_decision["nextAction"] = "switch_topic"
    agent_decision["focus"] = focus
    agent_decision["guardrailApplied"] = True
    agent_decision["topicShift"] = {"from": previous_focus, "to": str(focus or "").strip()}
    agent_decision["debugSignals"] = build_debug_signals(None, agent_decision)
    agent_decision["reason"] = f"{agent_decision.get('reason') or ''} {reason}".strip()
    agent_decision["decisionSummary"] = f"{agent_decision.get('decisionSummary') or agent_decision['reason']} {reason}".strip()


def normalize_next_question_result(
    result: dict[str, Any],
    *,
    payload: QuestionRequest,
    agent_decision: dict[str, Any],
) -> dict[str, str]:
    focus = normalize_next_question_focus(result, agent_decision, payload.profile)
    prompt = str(result.get("prompt") or "").strip()
    last_answer = payload.history[-1] if payload.history else {}
    if classify_answer_status(str(last_answer.get("answer") or "")) == "不会":
        prompt = soften_prompt_for_weak_answer(prompt, focus, agent_decision)
    if is_repeated_prompt(prompt, payload.history):
        focus = select_alternative_focus(focus, payload.profile)
        prompt = build_switch_focus_prompt(focus, payload.agentMode)
        record_repeated_prompt_guardrail(agent_decision, focus)
    return {
        "stage": str(result.get("stage") or agent_decision["stage"]),
        "stability": str(result.get("stability") or f"Agent:{agent_decision['nextAction']}"),
        "focus": focus,
        "prompt": prompt,
    }


def build_model_provider_fallback_question(
    *,
    payload: QuestionRequest,
    agent_decision: dict[str, Any],
    error: Exception,
) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
    focus = str(agent_decision.get("focus") or "").strip()
    if not focus:
        focus = infer_question_focus(
            str(payload.profile.get("targetRole") or ""),
            str(payload.profile.get("resume") or ""),
            str(payload.profile.get("jd") or ""),
            str((payload.history[-1] if payload.history else {}).get("question") or ""),
            fallback="稳定性降级追问",
        )
    focus = focus[:16]
    stage = str(agent_decision.get("stage") or payload.nextStage or "技术追问")
    prompt = (
        f"模型服务暂时不可用，我们先用稳定兜底问题继续训练。围绕「{focus}」，"
        "请你先用自己的话解释一个核心概念，再补充一个你项目里可能怎么落地的例子。"
    )
    trigger_rules = agent_decision.get("triggerRules") if isinstance(agent_decision.get("triggerRules"), list) else []
    if "model_provider_fallback" not in trigger_rules:
        trigger_rules = [*trigger_rules, "model_provider_fallback"]
    fallback_decision = {
        **agent_decision,
        "nextAction": agent_decision.get("nextAction") or "lower_difficulty",
        "stage": stage,
        "difficulty": agent_decision.get("difficulty") or "basic",
        "focus": focus,
        "fallbackUsed": True,
        "guardrailApplied": True,
        "triggerRules": trigger_rules,
        "reason": "模型供应商请求失败，后端使用安全兜底问题保持训练流程不中断。",
        "decisionSummary": "模型供应商请求失败，本轮已切换为安全兜底问题，避免前端训练流程中断。",
        "providerError": str(getattr(error, "detail", error)),
    }
    quality_gate = {
        "passed": False,
        "fallbackToClassic": True,
        "riskLevel": "medium",
        "reasons": ["模型供应商请求失败"],
        "checks": {
            "modelProviderAvailable": False,
            "safeFallbackQuestion": True,
        },
    }
    return (
        {
            "stage": stage,
            "stability": "模型降级兜底",
            "focus": focus,
            "prompt": prompt,
        },
        fallback_decision,
        quality_gate,
    )


async def safe_call_question_model(*, messages: list[dict[str, Any]], temperature: float) -> dict[str, Any]:
    try:
        return await call_model(messages=messages, temperature=temperature)
    except HTTPException as exc:
        return {"__provider_error__": exc}


def normalize_string_list(value: Any, *, limit: int = 3, fallback: list[str] | None = None) -> list[str]:
    if not isinstance(value, list):
        return fallback or []
    items = [str(item).strip() for item in value if str(item).strip()]
    return items[:limit] or (fallback or [])


def fallback_question_review(answer: dict[str, Any], index: int) -> dict[str, Any]:
    focus = str(answer.get("focus") or answer.get("stage") or "综合能力").strip()
    question = str(answer.get("question") or "本题未记录问题文本").strip()
    answer_text = str(answer.get("answer") or "").strip()
    status = classify_answer_status(answer_text)
    missing_points = ["概念解释", "项目例子", "验证方式"] if status != "完整" else ["量化结果", "技术取舍", "复盘总结"]
    training_action = f"围绕「{focus}」准备一段 1 分钟回答，至少包含一个项目细节和一个验证方式。"
    return {
        "index": index,
        "focus": focus,
        "question": question,
        "answerStatus": status,
        "whyAsked": f"这道题用于确认你对「{focus}」的理解和表达是否扎实。",
        "missingPoints": missing_points,
        "referenceDirection": "建议按背景、做法、原因、结果的顺序组织回答，并补充一个项目中的具体例子。",
        "trainingAction": training_action,
        "weakTags": merge_weak_tags(
            focus=focus,
            text=" ".join([question, answer_text, *missing_points, training_action]),
        ),
    }


def normalize_question_review(review: Any, answer: dict[str, Any], index: int) -> dict[str, Any]:
    fallback = fallback_question_review(answer, index)
    if not isinstance(review, dict):
        return fallback
    status = str(review.get("answerStatus") or fallback["answerStatus"]).strip()
    if status not in ALLOWED_ANSWER_STATUSES:
        status = fallback["answerStatus"]
    focus = str(review.get("focus") or fallback["focus"]).strip()
    question = str(review.get("question") or fallback["question"]).strip()
    missing_points = normalize_string_list(review.get("missingPoints"), fallback=fallback["missingPoints"])
    training_action = str(review.get("trainingAction") or fallback["trainingAction"]).strip()
    return {
        "index": int(review.get("index") or index),
        "focus": focus,
        "question": question,
        "answerStatus": status,
        "whyAsked": str(review.get("whyAsked") or fallback["whyAsked"]).strip(),
        "missingPoints": missing_points,
        "referenceDirection": str(review.get("referenceDirection") or fallback["referenceDirection"]).strip(),
        "trainingAction": training_action,
        "weakTags": merge_weak_tags(
            review.get("weakTags"),
            fallback.get("weakTags"),
            focus=focus,
            text=" ".join([question, *missing_points, training_action]),
        ),
    }


def build_question_reviews(result: dict[str, Any], answers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    model_reviews = result.get("questionReviews")
    reviews = model_reviews if isinstance(model_reviews, list) else []
    return [
        normalize_question_review(reviews[index] if index < len(reviews) else None, answer, index + 1)
        for index, answer in enumerate(answers)
    ]


def normalize_weak_topics(value: Any, question_reviews: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    topics = value if isinstance(value, list) else []
    normalized = []
    for item in topics:
        if not isinstance(item, dict):
            continue
        focus = str(item.get("focus") or "").strip()
        if not focus:
            continue
        reason = str(item.get("reason") or "本轮回答暴露出该考察点仍需补强。").strip()
        training_action = str(item.get("trainingAction") or f"围绕「{focus}」准备一段 1 分钟回答。").strip()
        normalized.append(
            {
                "focus": focus,
                "reason": reason,
                "trainingAction": training_action,
                "weakTags": merge_weak_tags(item.get("weakTags"), focus=focus, text=f"{reason} {training_action}"),
            }
        )
        if len(normalized) >= limit:
            break
    if normalized:
        return normalized

    fallback_topics = []
    for review in question_reviews:
        if review.get("answerStatus") == "完整":
            continue
        focus = str(review.get("focus") or "综合能力").strip()
        training_action = str(review.get("trainingAction") or f"围绕「{focus}」准备一段 1 分钟回答。").strip()
        fallback_topics.append(
            {
                "focus": focus,
                "reason": "本题回答未达到完整状态，需要补充缺失点和项目例子。",
                "trainingAction": training_action,
                "weakTags": merge_weak_tags(review.get("weakTags"), focus=focus, text=training_action),
            }
        )
        if len(fallback_topics) >= limit:
            break
    return fallback_topics


def build_training_plan(result: dict[str, Any], question_reviews: list[dict[str, Any]]) -> dict[str, Any]:
    model_plan = result.get("trainingPlan") if isinstance(result.get("trainingPlan"), dict) else {}
    weak_topics = normalize_weak_topics(model_plan.get("weakTopics"), question_reviews)
    weak_focuses = [topic["focus"] for topic in weak_topics]
    next_round_priority = normalize_string_list(
        model_plan.get("nextRoundPriority"),
        fallback=weak_focuses or ["自我介绍", "项目表达", "技术基础"],
    )
    practice_questions = normalize_string_list(
        model_plan.get("practiceQuestions"),
        fallback=[
            f"请用 1 分钟说明「{focus}」的核心概念、项目做法和验证方式。"
            for focus in (weak_focuses or ["本轮最薄弱的考察点"])
        ],
    )
    one_minute_templates = normalize_string_list(
        model_plan.get("oneMinuteTemplates"),
        fallback=[
            f"背景：面试官追问「{focus}」；做法：先解释概念，再讲项目实现；结果：补充验证方式和改进点。"
            for focus in (weak_focuses or ["本轮薄弱点"])
        ],
    )
    should_retry = bool(model_plan.get("shouldRetry", any(review.get("answerStatus") != "完整" for review in question_reviews)))
    return {
        "weakTopics": weak_topics,
        "nextRoundPriority": next_round_priority,
        "practiceQuestions": practice_questions,
        "oneMinuteTemplates": one_minute_templates,
        "shouldRetry": should_retry,
    }


@router.post("/next-question", response_model=QuestionResponse)
async def next_question(
    payload: QuestionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    enforce_rate_limit("interview.next_question", client_identity(request, user_id=current_user.id))
    runtime_policy = decide_runtime_policy(
        requested_runtime=payload.agentRuntime,
        user_role=current_user.role,
        agent_mode=payload.agentMode,
    )
    agent_result = await run_next_question_agent(
        profile=payload.profile,
        history=payload.history,
        next_stage=payload.nextStage,
        agent_mode=payload.agentMode,
        role_retrieve_fn=retrieve_role_context,
        question_retrieve_fn=retrieve_questions,
        memory_retrieve_fn=lambda profile, limit: retrieve_candidate_memory(
            db,
            profile,
            limit=limit,
            user_id=current_user.id,
            application_profile_id=payload.applicationProfileId,
        ),
        role_retrieve_kwargs={"db": db, "user_id": current_user.id},
        question_retrieve_kwargs={"db": db, "user_id": current_user.id},
        call_model_fn=call_model,
    )
    role_hits = agent_result["roleHits"]
    question_hits = agent_result["questionHits"]
    memories = agent_result["memoryHits"]
    agent_state = agent_result["agentState"]
    agent_decision = agent_result["agentDecision"]
    candidate_training_tasks = list_candidate_training_tasks(
        db,
        user_id=current_user.id,
        application_profile_id=payload.applicationProfileId,
        limit=3,
    )
    selected_training_task = select_agent_training_task(candidate_training_tasks, agent_mode=payload.agentMode)
    agent_state["candidateTrainingTasks"] = candidate_training_tasks
    if selected_training_task:
        agent_decision["selectedTrainingTask"] = {
            "id": selected_training_task.get("id"),
            "weakTag": selected_training_task.get("weakTag"),
            "title": selected_training_task.get("title"),
            "masteryScore": selected_training_task.get("masteryScore"),
            "priority": selected_training_task.get("priority"),
            "reason": selected_training_task.get("reason"),
        }
    query_text = build_rag_query(payload.profile, payload.nextStage)
    log_retrievals(
        db,
        current_user=current_user,
        application_profile_id=payload.applicationProfileId,
        request_type="next_question",
        query_text=query_text,
        role_hits=role_hits,
        question_hits=question_hits,
        memory_hits=memories,
    )
    role_context = format_role_context(role_hits)
    question_context = format_question_context(question_hits)
    candidate_context = format_candidate_memory(memories)
    candidate_profile_context = format_candidate_profile(build_candidate_profile(memories))
    provider_quality_gate: dict[str, Any] | None = None
    result = await safe_call_question_model(
        temperature=0.7,
        messages=[
            {
                "role": "system",
                "content": NEXT_QUESTION_SYSTEM_PROMPT,
            },
            build_context_message("岗位知识库 RAG 命中资料", role_context),
            build_context_message("题库 RAG 命中资料", question_context),
            build_context_message("候选人画像 RAG 命中资料", candidate_context),
            build_context_message("候选人长期训练画像", candidate_profile_context),
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "profile": payload.profile,
                        "history": payload.history,
                        "nextStage": payload.nextStage,
                        "agentDecision": agent_decision,
                        "candidateTrainingTasks": candidate_training_tasks,
                        **build_question_strategy_payload(
                            history=payload.history,
                            role_hits=role_hits,
                            question_hits=question_hits,
                            memory_hits=memories,
                            agent_mode=payload.agentMode,
                            agent_decision=agent_decision,
                        ),
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )

    if result.get("__provider_error__"):
        normalized_question, agent_decision, provider_quality_gate = build_model_provider_fallback_question(
            payload=payload,
            agent_decision=agent_decision,
            error=result["__provider_error__"],
        )
    elif not result.get("prompt"):
        raise HTTPException(status_code=500, detail="Model did not return a next question.")
    else:
        normalized_question = normalize_next_question_result(result, payload=payload, agent_decision=agent_decision)
    rag_reasons = [
        build_user_rag_reason(retriever_name="role_knowledge", hits=role_hits, focus=normalized_question["focus"]),
        build_user_rag_reason(retriever_name="question_bank", hits=question_hits, focus=normalized_question["focus"]),
        build_user_rag_reason(retriever_name="candidate_memory", hits=memories, focus=normalized_question["focus"]),
    ]
    append_generate_question_trace(
        agent_state=agent_state,
        agent_decision=agent_decision,
        normalized_question=normalized_question,
        role_hits=role_hits,
        question_hits=question_hits,
        memory_hits=memories,
    )
    append_update_memory_trace(
        agent_state=agent_state,
        agent_decision=agent_decision,
        normalized_question=normalized_question,
    )
    runtime_audit = build_runtime_audit(
        policy=runtime_policy,
        quality_gate=provider_quality_gate,
        checkpoint_summary={},
        comparison_summary={},
        visible_runtime="classic",
    )
    classic_response = {
        **normalized_question,
        "agentDecision": agent_decision,
        "decisionSummary": agent_decision.get("decisionSummary") or agent_decision.get("reason") or "",
        "ragReasons": rag_reasons,
        "runtimeAudit": runtime_audit,
        "workflowTrace": [],
        "checkpointSummary": {},
        "qualityGate": provider_quality_gate or {},
        "fallbackSummary": {
            "used": bool(runtime_audit.get("fallbackUsed")),
            "reason": "; ".join(runtime_audit.get("qualityGateReasons") or []),
        },
    }
    runtime_thread_id = f"interview-{current_user.id}-{payload.applicationProfileId or 'none'}-{len(payload.history)}"

    def write_agent_log(*, audit: dict[str, Any], quality_gate: dict[str, Any] | None = None) -> None:
        agent_state["threadId"] = runtime_thread_id
        agent_state["runtimeAudit"] = audit
        agent_decision["runtimeAudit"] = audit
        if isinstance(quality_gate, dict):
            agent_decision["qualityGate"] = quality_gate
        create_agent_decision_log(
            db,
            user_id=current_user.id,
            application_profile_id=payload.applicationProfileId,
            request_type="next_question",
            state=agent_state,
            decision=agent_decision,
        )

    if runtime_policy["allowedRuntime"] in {"shadow", "langgraph", "langgraph_mainline"}:
        async def classic_runner(**kwargs: Any) -> dict[str, Any]:
            return {
                "question": {
                    "stage": classic_response["stage"],
                    "stability": classic_response["stability"],
                    "focus": classic_response["focus"],
                    "prompt": classic_response["prompt"],
                    "content": classic_response["prompt"],
                },
                "decision": agent_decision,
                "status": "completed",
            }

        def retrieve_context_for_graph(profile: dict[str, Any], next_stage: str) -> dict[str, Any]:
            return retrieve_real_context_for_graph(
                profile=profile,
                next_stage=next_stage,
                role_retrieve_fn=retrieve_role_context,
                question_retrieve_fn=retrieve_questions,
                memory_retrieve_fn=lambda profile, limit: retrieve_candidate_memory(
                    db,
                    profile,
                    limit=limit,
                    user_id=current_user.id,
                    application_profile_id=payload.applicationProfileId,
                ),
                role_retrieve_kwargs={"db": db, "user_id": current_user.id},
                question_retrieve_kwargs={"db": db, "user_id": current_user.id},
            )

        async def decide_action_for_graph(**kwargs: Any) -> dict[str, Any]:
            return await decide_real_action_for_graph(call_model_fn=call_model, **kwargs)

        async def langgraph_runner(**kwargs: Any) -> dict[str, Any]:
            return await run_langgraph_agent_v2(
                thread_id=runtime_thread_id,
                application_profile_id=payload.applicationProfileId,
                profile=payload.profile,
                history=payload.history,
                next_stage=payload.nextStage,
                agent_mode=payload.agentMode,
                use_real_rag=True,
                use_real_decision=True,
                retrieve_context_fn=retrieve_context_for_graph,
                decide_action_fn=decide_action_for_graph,
            )

        runtime_result = await run_agent_runtime(
            agent_runtime=(
                "shadow"
                if runtime_policy["allowedRuntime"] == "shadow"
                else "langgraph_canary"
                if runtime_policy["requestedRuntime"] == "langgraph_canary"
                else "langgraph_mainline"
            ),
            thread_id=runtime_thread_id,
            classic_runner=classic_runner,
            langgraph_runner=langgraph_runner,
            payload={
                "answer": str((payload.history[-1] if payload.history else {}).get("answer") or ""),
                "recentQuestions": [str(item.get("question") or "") for item in payload.history if item.get("question")],
            },
        )
        runtime_audit = runtime_result.get("runtimeAudit") if isinstance(runtime_result.get("runtimeAudit"), dict) else runtime_audit
        shadow_result = runtime_result.get("shadow") if isinstance(runtime_result.get("shadow"), dict) else {}
        runtime_checkpoint_summary = (
            runtime_result.get("checkpointSummary") if isinstance(runtime_result.get("checkpointSummary"), dict) else {}
        )
        checkpoint_summary = (
            shadow_result.get("checkpointSummary")
            if isinstance(shadow_result.get("checkpointSummary"), dict)
            else runtime_checkpoint_summary
        )
        if checkpoint_summary:
            checkpoint_summary["runtimeAudit"] = runtime_audit
            checkpoint_summary["qualityGate"] = runtime_result.get("qualityGate") if isinstance(runtime_result.get("qualityGate"), dict) else {}
            checkpoint_summary["comparisonSummary"] = (
                runtime_result.get("comparisonSummary") if isinstance(runtime_result.get("comparisonSummary"), dict) else {}
            )
            checkpoint_summary_store.save_summary(checkpoint_summary)
            save_checkpoint_summary(db, checkpoint_summary)
        if runtime_result.get("visibleRuntime") in {"langgraph", "langgraph_mainline"}:
            question = runtime_result.get("question") if isinstance(runtime_result.get("question"), dict) else {}
            prompt = str(question.get("prompt") or question.get("content") or classic_response["prompt"])
            decision = runtime_result.get("decision") if isinstance(runtime_result.get("decision"), dict) else {}
            write_agent_log(audit=runtime_audit, quality_gate=runtime_result.get("qualityGate") if isinstance(runtime_result.get("qualityGate"), dict) else {})
            return {
                "stage": str(question.get("stage") or classic_response["stage"]),
                "stability": str(question.get("stability") or classic_response["stability"]),
                "focus": str(question.get("focus") or classic_response["focus"]),
                "prompt": prompt,
                "agentDecision": {
                    **decision,
                    "runtimeAudit": runtime_audit,
                    "qualityGate": runtime_result.get("qualityGate") or {},
                },
                "decisionSummary": str(decision.get("decisionSummary") or decision.get("reason") or classic_response["decisionSummary"]),
                "ragReasons": rag_reasons,
                "runtimeAudit": runtime_audit,
                "workflowTrace": runtime_result.get("runtimeTrace") if isinstance(runtime_result.get("runtimeTrace"), list) else [],
                "checkpointSummary": runtime_checkpoint_summary,
                "qualityGate": runtime_result.get("qualityGate") if isinstance(runtime_result.get("qualityGate"), dict) else {},
                "fallbackSummary": {"used": False, "reason": ""},
            }
        classic_response["runtimeAudit"] = runtime_audit
        classic_response["workflowTrace"] = runtime_result.get("runtimeTrace") if isinstance(runtime_result.get("runtimeTrace"), list) else []
        classic_response["checkpointSummary"] = runtime_checkpoint_summary
        classic_response["qualityGate"] = runtime_result.get("qualityGate") if isinstance(runtime_result.get("qualityGate"), dict) else {}
        classic_response["fallbackSummary"] = {
            "used": bool(runtime_audit.get("fallbackUsed")),
            "reason": "; ".join(runtime_audit.get("qualityGateReasons") or []),
        }
        classic_response["agentDecision"] = {
            **agent_decision,
            "runtimeAudit": runtime_audit,
            "qualityGate": runtime_result.get("qualityGate") or {},
        }

    write_agent_log(
        audit=classic_response["runtimeAudit"],
        quality_gate=classic_response.get("agentDecision", {}).get("qualityGate")
        if isinstance(classic_response.get("agentDecision"), dict)
        else None,
    )
    return classic_response


@router.post("/report", response_model=ReportResponse)
async def interview_report(
    payload: ReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    role_hits = retrieve_role_context(payload.profile, "面试报告", limit=4, db=db, user_id=current_user.id)
    question_hits = retrieve_questions(payload.profile, "面试报告", limit=4, db=db, user_id=current_user.id)
    memories = retrieve_candidate_memory(
        db,
        payload.profile,
        limit=5,
        user_id=current_user.id,
        application_profile_id=payload.applicationProfileId,
    )
    query_text = build_rag_query(
        payload.profile,
        "面试报告",
        extra_text=" ".join(str(answer.get("answer") or "") for answer in payload.answers),
    )
    log_retrievals(
        db,
        current_user=current_user,
        application_profile_id=payload.applicationProfileId,
        request_type="report",
        query_text=query_text,
        role_hits=role_hits,
        question_hits=question_hits,
        memory_hits=memories,
    )
    role_context = format_role_context(role_hits)
    question_context = format_question_context(question_hits)
    candidate_context = format_candidate_memory(memories)
    candidate_profile_context = format_candidate_profile(build_candidate_profile(memories))
    result = await call_model(
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": REPORT_SYSTEM_PROMPT,
            },
            build_context_message("岗位知识库 RAG 命中资料", role_context),
            build_context_message("题库 RAG 命中资料", question_context),
            build_context_message("候选人画像 RAG 命中资料", candidate_context),
            build_context_message("候选人长期训练画像", candidate_profile_context),
            {
                "role": "user",
                "content": json.dumps(
                    {"profile": payload.profile, "answers": payload.answers},
                    ensure_ascii=False,
                ),
            },
        ],
    )

    question_reviews = build_question_reviews(result, payload.answers)
    return {
        "score": int(result.get("score") or 60),
        "strengths": result.get("strengths") or [],
        "risks": result.get("risks") or [],
        "actions": result.get("actions") or [],
        "questionReviews": question_reviews,
        "trainingPlan": build_training_plan(result, question_reviews),
    }
