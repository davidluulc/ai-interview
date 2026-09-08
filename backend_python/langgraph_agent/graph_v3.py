"""LangGraph v3 图的规划（plan）节点：模型驱动选工具 + 策略护栏 + 强制收敛。"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

from backend_python.agent_trace import build_node_trace, summarize_text
from backend_python.structured_output import StructuredOutputExhausted

VALID_TOOLS = {
    "retrieve_role_knowledge",
    "retrieve_question_bank",
    "retrieve_candidate_memory",
}
MAX_PLANNING_STEPS = 2


class AgentPlanModel(BaseModel):
    """面试 Agent 规划节点输出：本轮检索哪些工具、检索什么、下一步做什么。

    selectedTools 必须是 VALID_TOOLS 的子集（三选多，可组合）；readyToAsk=true
    表示信息已足够直接出题，此时 selectedTools 可为空。
    """

    readyToAsk: bool
    selectedTools: list[str]
    toolQuery: str
    nextAction: str
    difficulty: str
    focus: str
    reason: str


PLAN_SYSTEM_PROMPT = (
    "你是面试 Agent 的规划者（planner）。每轮提问前，你需要决定："
    "本轮还需要检索哪些上下文、用什么查询词检索、以及对候选人下一步做什么。\n"
    "可用工具（三选多，可任意组合，信息足够时也可以都不选）：\n"
    "- retrieve_role_knowledge：岗位知识库——岗位 JD、技能要求、面试重点；\n"
    "- retrieve_question_bank：题库——历史题目、题目模板、考查覆盖面；\n"
    "- retrieve_candidate_memory：候选人画像——历史表现、弱项、训练偏好。\n"
    "只输出一个 JSON 对象，字段：\n"
    "- readyToAsk：信息是否已足够直接出题，足够则为 true；\n"
    "- selectedTools：本轮要调用的工具名列表，必须是上述清单的子集；\n"
    "- toolQuery：本轮检索的统一查询词，不检索时为空字符串；\n"
    "- nextAction：deep_follow_up | lower_difficulty | switch_topic | end_interview；\n"
    "- difficulty：basic | medium | hard；\n"
    "- focus：本轮聚焦的知识点或能力；\n"
    "- reason：这样规划的简短理由。\n"
    "规划规则：只有当已有信息不足以出高质量题目时才选择工具并置 readyToAsk=false；"
    "信息足够时 selectedTools 置空数组并置 readyToAsk=true，不要再检索。"
)


def _trace_list(state: dict[str, Any]) -> list[dict[str, Any]]:
    return list(state.get("nodeTrace") or [])


def build_plan_messages(state: dict[str, Any]) -> list[dict[str, Any]]:
    """纯函数：把图状态组装成规划模型的 system+user 消息。"""
    profile = dict(state.get("profile") or {})
    recent_history = [
        {
            "question": summarize_text(item.get("question"), limit=60),
            "answer": summarize_text(item.get("answer"), limit=120),
        }
        for item in list(state.get("history") or [])[-3:]
        if isinstance(item, dict)
    ]
    policy = dict(state.get("policy") or {})
    payload = {
        "profileSummary": {"targetRole": str(profile.get("targetRole") or "AI 应用开发")},
        "recentHistory": recent_history,
        "policyAdvice": {
            "recommendedAction": str(policy.get("recommendedAction") or ""),
            "difficulty": str(policy.get("difficulty") or ""),
            "reasons": [str(reason) for reason in list(policy.get("policyReasons") or [])[:3]],
        },
        "remainingRounds": int(state.get("remainingRounds") or 0),
    }
    return [
        {"role": "system", "content": PLAN_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def apply_policy_guardrail(plan: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """纯函数：policy 强触发时覆盖模型规划，并把 selectedTools 收敛到合法工具集。"""
    guarded = dict(plan)
    guarded["selectedTools"] = [tool for tool in list(guarded.get("selectedTools") or []) if tool in VALID_TOOLS]
    reasons = [str(reason).strip() for reason in list(policy.get("policyReasons") or []) if str(reason).strip()]
    if policy.get("recommendedAction") == "switch_topic" and guarded.get("nextAction") != "switch_topic":
        guarded["nextAction"] = "switch_topic"
        guarded["difficulty"] = str(policy.get("difficulty") or guarded.get("difficulty") or "basic")
        guarded["overrideReason"] = "；".join(reasons[:2]) or "策略建议切换话题。"
        guarded["decisionSource"] = "guardrail"
    else:
        guarded["decisionSource"] = "model"
    return guarded


def make_plan_node(
    structured_call_fn: Callable[..., Awaitable[tuple[Any, dict[str, Any]]]],
) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
    """工厂：返回 v3 图的 plan 节点函数，写 planDecision/decision/planningSteps/nodeTrace。"""

    async def plan_node(state: dict[str, Any]) -> dict[str, Any]:
        policy = dict(state.get("policy") or {})
        planning_steps = int(state.get("planningSteps") or 0) + 1
        fallback_used = False
        error_summary = ""
        try:
            model, _chain_meta = await structured_call_fn(
                messages=build_plan_messages(state),
                schema_model=AgentPlanModel,
                temperature=0.2,
            )
            plan = apply_policy_guardrail(model.model_dump(), policy)
            decision_source = str(plan.get("decisionSource") or "model")
        except Exception as exc:  # StructuredOutputExhausted 及其他异常统一降级
            error_summary = summarize_text(
                "structured_output_exhausted" if isinstance(exc, StructuredOutputExhausted) else exc,
                limit=120,
            )
            fallback_used = True
            decision_source = "fallback"
            plan = {
                "readyToAsk": True,
                "selectedTools": [],
                "toolQuery": "",
                "nextAction": str(policy.get("recommendedAction") or "deep_follow_up"),
                "difficulty": str(policy.get("difficulty") or "medium"),
                "focus": str(state.get("nextStage") or "综合追问"),
                "reason": f"规划模型调用失败（{error_summary}），降级使用策略推荐动作。",
                "decisionSource": "fallback",
            }
        if planning_steps >= MAX_PLANNING_STEPS:
            plan["readyToAsk"] = True
        decision = {
            "nextAction": str(plan.get("nextAction") or ""),
            "stage": str(state.get("nextStage") or "综合追问"),
            "difficulty": str(plan.get("difficulty") or "medium"),
            "focus": str(plan.get("focus") or ""),
            "reason": str(plan.get("reason") or ""),
            "decisionSource": decision_source,
            "fallbackUsed": fallback_used,
        }
        return {
            "planDecision": plan,
            "decision": decision,
            "planningSteps": planning_steps,
            "nodeTrace": [
                *_trace_list(state),
                build_node_trace(
                    node_name="plan",
                    input_summary={
                        "historyCount": len(state.get("history") or []),
                        "policyRecommendedAction": str(policy.get("recommendedAction") or ""),
                    },
                    output_summary={
                        "nextAction": decision["nextAction"],
                        "readyToAsk": bool(plan.get("readyToAsk")),
                        "selectedTools": list(plan.get("selectedTools") or []),
                        "decisionSource": decision_source,
                    },
                    fallback_used=fallback_used,
                    error=error_summary,
                ),
            ],
        }

    return plan_node
