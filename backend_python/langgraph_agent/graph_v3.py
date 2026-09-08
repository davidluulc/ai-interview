"""LangGraph v3 图：plan 节点（模型驱动选工具 + 策略护栏）+ tools 节点 + 条件路由 + 图组装。"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from backend_python.agent_trace import build_node_trace, build_tool_call_summary, summarize_text
from backend_python.langgraph_agent.checkpoint_store import empty_checkpoint_summary, normalize_thread_id
from backend_python.langgraph_agent.nodes import (
    analyze_answer_node,
    apply_policy_node,
    generate_question_node,
    observe_state_node,
    update_memory_node,
)
from backend_python.langgraph_agent.state import (
    InterviewGraphState,
    assert_graph_state_jsonable,
    build_initial_graph_state,
)
from backend_python.structured_output import StructuredOutputExhausted

logger = logging.getLogger(__name__)

VALID_TOOLS = {
    "retrieve_role_knowledge",
    "retrieve_question_bank",
    "retrieve_candidate_memory",
}
MAX_PLANNING_STEPS = 2
V3_RECURSION_LIMIT = 25

TOOL_RESULT_BUCKETS = {
    "retrieve_role_knowledge": "role",
    "retrieve_question_bank": "question",
    "retrieve_candidate_memory": "memory",
}


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
                        "overrideReason": str(plan.get("overrideReason") or ""),
                    },
                    fallback_used=fallback_used,
                    error=error_summary,
                ),
            ],
        }

    return plan_node


def route_after_plan(state: dict[str, Any]) -> str:
    """纯函数：plan 之后的条件路由，返回 "tools" | "generate" | "end"。

    - planDecision.nextAction == "end_interview" → "end"（直接收束，state 原样保留）；
    - planDecision.readyToAsk 为真，或 planningSteps 已达 MAX_PLANNING_STEPS → "generate"；
    - 其余情况 → "tools"（回到检索循环，步数上限保证有界）。
    """
    plan_decision = dict(state.get("planDecision") or {})
    if str(plan_decision.get("nextAction") or "") == "end_interview":
        return "end"
    if plan_decision.get("readyToAsk") or int(state.get("planningSteps") or 0) >= MAX_PLANNING_STEPS:
        return "generate"
    return "tools"


def make_tools_node(
    tool_fns: dict[str, Callable[..., list[dict[str, Any]]]],
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """工厂：返回 v3 图的 tools 节点，只执行 planDecision.selectedTools 命中的工具。

    工具调用约定（Task 4 / S5 的真实检索工具必须满足）::

        tool_fn(profile: dict, next_stage: str, tool_query: str) -> list[dict]

    - profile：候选人画像（来自 state["profile"]）；
    - next_stage：本轮追问阶段（来自 state["nextStage"]）；
    - tool_query：plan 节点给出的统一检索词（planDecision["toolQuery"]）；
    - 返回值：命中条目列表 list[dict]；抛出的异常由本节点捕获并降级为空结果。

    节点返回 partial：selectedToolResults（固定 role/question/memory 三键，未选中
    或失败的工具对应空列表），以及 nodeTrace（含每个工具的 toolCall 摘要——
    命中数/成功位/错误信息——和 skippedTools 未选中工具列表，保证可观测性）。
    selectedTools 会被收敛到 tool_fns 实际注册的键；单个工具失败只影响自己的桶，
    不会中断其他工具。
    """

    def tools_node(state: dict[str, Any]) -> dict[str, Any]:
        plan_decision = dict(state.get("planDecision") or {})
        selected_tools = [
            tool_name
            for tool_name in list(plan_decision.get("selectedTools") or [])
            if tool_name in tool_fns
        ]
        skipped_tools = [tool_name for tool_name in tool_fns if tool_name not in selected_tools]
        profile = dict(state.get("profile") or {})
        next_stage = str(state.get("nextStage") or "")
        tool_query = str(plan_decision.get("toolQuery") or "")
        selected_tool_results: dict[str, list[dict[str, Any]]] = {"role": [], "question": [], "memory": []}
        tool_calls: list[dict[str, Any]] = []
        for tool_name in selected_tools:
            hits: list[dict[str, Any]] = []
            error = ""
            success = True
            try:
                hits = list(
                    tool_fns[tool_name](profile=profile, next_stage=next_stage, tool_query=tool_query) or []
                )
            except Exception as exc:  # 单个工具失败不能拖垮其他工具
                logger.warning("tools 节点工具 %s 调用失败：%s", tool_name, exc)
                error = summarize_text(exc, limit=120)
                success = False
                hits = []
            bucket = TOOL_RESULT_BUCKETS.get(tool_name)
            if bucket is not None:
                selected_tool_results[bucket] = hits
            tool_calls.append(
                build_tool_call_summary(
                    tool_name=tool_name,
                    input_summary={"toolQuery": tool_query},
                    output_summary={"hitCount": len(hits)},
                    success=success,
                    error=error,
                )
            )
        return {
            "selectedToolResults": selected_tool_results,
            "nodeTrace": [
                *_trace_list(state),
                build_node_trace(
                    node_name="tools",
                    input_summary={
                        "selectedTools": selected_tools,
                        "toolQuery": tool_query,
                    },
                    output_summary={
                        "roleHitCount": len(selected_tool_results["role"]),
                        "questionHitCount": len(selected_tool_results["question"]),
                        "memoryHitCount": len(selected_tool_results["memory"]),
                        "skippedTools": skipped_tools,
                        "toolCalls": tool_calls,
                    },
                    fallback_used=any(not call["success"] for call in tool_calls),
                ),
            ],
        }

    return tools_node


def build_interview_graph_v3(
    *,
    structured_call_fn: Callable[..., Awaitable[tuple[Any, dict[str, Any]]]],
    tool_fns: dict[str, Callable[..., list[dict[str, Any]]]],
):
    """组装 v3 面试图：observe_state → analyze_answer → apply_policy → plan ⇄ tools → generate_question → update_memory → END。

    apply_policy 在 plan 之前执行：analyze_answer 产出的 answerAnalysis 喂给
    规则策略引擎（agent_policy.apply_agent_policy），policy 结果写入 state，
    供 build_plan_messages 的 policyAdvice 与 apply_policy_guardrail 的强触发
    覆盖消费——保证「模型建议、规则执行」分层在 v3 图内闭环。

    条件路由 route_after_plan：end_interview 直接收束到 END；readyToAsk 或规划步数
    超限（MAX_PLANNING_STEPS）走 generate_question；否则进 tools 执行本轮选中的
    检索工具后回到 plan，形成有界循环。

    v3.0 不接 checkpointer：断点续跑/回放依赖图之外的线程状态持久化实现，
    checkpointer 集成延后（deferred），避免与 v2 图的 memory saver 语义混用。
    """
    graph = StateGraph(InterviewGraphState)
    graph.add_node("observe_state", observe_state_node)
    graph.add_node("analyze_answer", analyze_answer_node)
    graph.add_node("apply_policy", apply_policy_node)
    graph.add_node("plan", make_plan_node(structured_call_fn))
    graph.add_node("tools", make_tools_node(tool_fns))
    graph.add_node("generate_question", generate_question_node)
    graph.add_node("update_memory", update_memory_node)

    graph.add_edge(START, "observe_state")
    graph.add_edge("observe_state", "analyze_answer")
    graph.add_edge("analyze_answer", "apply_policy")
    graph.add_edge("apply_policy", "plan")
    graph.add_conditional_edges(
        "plan",
        route_after_plan,
        {"tools": "tools", "generate": "generate_question", "end": END},
    )
    graph.add_edge("tools", "plan")
    graph.add_edge("generate_question", "update_memory")
    graph.add_edge("update_memory", END)
    return graph.compile()


def build_v3_invoke_config(thread_id: str) -> dict[str, Any]:
    """v3 的 ainvoke config：recursion_limit 死循环兜底 + thread_id 归一化。

    对齐 v2 checkpoint.build_graph_config 的 configurable.thread_id 归一化模式；
    额外带上 recursion_limit，作为 MAX_PLANNING_STEPS 之外的第二道保险
    （即使路由逻辑回归失效，LangGraph 也会在超限时抛 GraphRecursionError
    而不是无限挂起）。
    """
    return {
        "recursion_limit": V3_RECURSION_LIMIT,
        "configurable": {"thread_id": normalize_thread_id(thread_id)},
    }


async def run_interview_graph_v3(
    *,
    thread_id: str,
    profile: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
    next_stage: str = "",
    agent_mode: str = "interview",
    application_profile_id: int | None = None,
    structured_call_fn: Callable[..., Awaitable[tuple[Any, dict[str, Any]]]],
    tool_fns: dict[str, Callable[..., list[dict[str, Any]]]],
) -> dict[str, Any]:
    """v3 runner 封装：初始 state 组装 → graph.ainvoke → 结果信封补齐。

    与 v2 的 run_interview_graph_v2 对齐的部分：build_initial_graph_state 组装
    初始状态（thread_id / application_profile_id / profile / history /
    next_stage / agent_mode），返回 dict(result) 并附加 "threadId"
    （空值归一为 "default-thread"），最终 assert_graph_state_jsonable。

    与 v2 不同的部分：v3.0 的图不接 checkpointer（见
    build_interview_graph_v3），因此 config 里的 configurable.thread_id 仅保留
    trace 兼容、不做断点持久化；checkpointSummary 复用
    checkpoint_store.empty_checkpoint_summary 的键面（下游 _runtime_response /
    质量门按 v2 键面读取，避免 KeyError），但把 enabled 置为 False 表示
    v3.0 检查点未启用。
    """
    state = build_initial_graph_state(
        thread_id=thread_id,
        application_profile_id=application_profile_id,
        profile=profile,
        history=history,
        next_stage=next_stage,
        agent_mode=agent_mode,
    )
    graph = build_interview_graph_v3(structured_call_fn=structured_call_fn, tool_fns=tool_fns)
    result = dict(await graph.ainvoke(state, config=build_v3_invoke_config(thread_id)))
    checkpoint_summary = empty_checkpoint_summary(thread_id)
    checkpoint_summary["enabled"] = False
    result["checkpointSummary"] = checkpoint_summary
    result["threadId"] = str(thread_id or "default-thread")
    assert_graph_state_jsonable(result)
    return result
