from typing import Any

from backend_python.agent_policy import apply_agent_policy
from backend_python.agent_state import _analyze_answer_history, _classify_answer_status
from backend_python.agent_trace import build_node_trace, build_tool_call_summary


def _trace_list(state: dict[str, Any]) -> list[dict[str, Any]]:
    return list(state.get("nodeTrace") or [])


def observe_state_node(state: dict[str, Any]) -> dict[str, Any]:
    history = list(state.get("history") or [])
    round_count = len(history)
    remaining_rounds = max(8 - round_count, 0)
    return {
        "roundCount": round_count,
        "remainingRounds": remaining_rounds,
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="observe_state",
                input_summary={
                    "historyCount": round_count,
                    "agentMode": state.get("agentMode", "interview"),
                },
                output_summary={
                    "roundCount": round_count,
                    "remainingRounds": remaining_rounds,
                },
            ),
        ],
    }


def analyze_answer_node(state: dict[str, Any]) -> dict[str, Any]:
    history = list(state.get("history") or [])
    last_answer = history[-1] if history else {}
    answer_status = _classify_answer_status(str(last_answer.get("answer") or ""))
    analysis = dict(_analyze_answer_history(history))
    analysis["answerStatus"] = answer_status
    return {
        "answerAnalysis": analysis,
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="analyze_answer",
                input_summary={"historyCount": len(history)},
                output_summary={
                    "answerStatus": answer_status,
                    "weakAnswerStreak": analysis.get("weakAnswerStreak", 0),
                    "triggerSignals": analysis.get("triggerSignals", []),
                },
            ),
        ],
    }


def retrieve_context_node(state: dict[str, Any]) -> dict[str, Any]:
    target_role = str((state.get("profile") or {}).get("targetRole") or "AI 应用开发")
    role_hits = [
        {
            "id": "role-poc-1",
            "title": "岗位知识库样例",
            "content": f"{target_role} 需要理解 Agent、RAG 和工具调用。",
        }
    ]
    question_hits = [
        {
            "id": "question-poc-1",
            "title": "题库样例",
            "content": "请解释 RAG 的检索、重排和引用来源。",
        }
    ]
    memory_hits = [
        {
            "id": "memory-poc-1",
            "title": "候选人画像样例",
            "content": "候选人最近在 RAG 和 Agent 概念上需要降低难度训练。",
        }
    ]
    tool_calls = [
        build_tool_call_summary(
            tool_name="retrieve_role_knowledge",
            output_summary={"hitCount": len(role_hits)},
        ),
        build_tool_call_summary(
            tool_name="retrieve_question_bank",
            output_summary={"hitCount": len(question_hits)},
        ),
        build_tool_call_summary(
            tool_name="retrieve_candidate_memory",
            output_summary={"hitCount": len(memory_hits)},
        ),
    ]
    return {
        "roleHits": role_hits,
        "questionHits": question_hits,
        "memoryHits": memory_hits,
        "toolCalls": tool_calls,
        "retrievalQuality": {
            "roleKnowledge": {"level": "good", "hitCount": len(role_hits)},
            "questionBank": {"level": "good", "hitCount": len(question_hits)},
            "candidateMemory": {"level": "good", "hitCount": len(memory_hits)},
        },
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="retrieve_context",
                input_summary={"nextStage": state.get("nextStage", "")},
                output_summary={
                    "roleHitCount": len(role_hits),
                    "questionHitCount": len(question_hits),
                    "memoryHitCount": len(memory_hits),
                },
            ),
        ],
    }


def make_retrieve_context_v2_node(retrieve_context_fn):
    def retrieve_context_v2_node(state: dict[str, Any]) -> dict[str, Any]:
        result = retrieve_context_fn(
            profile=dict(state.get("profile") or {}),
            next_stage=str(state.get("nextStage") or ""),
        )
        tool_calls = list(result.get("toolCalls") or [])
        return {
            **result,
            "nodeTrace": [
                *_trace_list(state),
                build_node_trace(
                    node_name="retrieve_context",
                    input_summary={"nextStage": state.get("nextStage", "")},
                    output_summary={
                        "roleHitCount": len(result.get("roleHits") or []),
                        "questionHitCount": len(result.get("questionHits") or []),
                        "memoryHitCount": len(result.get("memoryHits") or []),
                    },
                    fallback_used=any(not call.get("success") for call in tool_calls),
                ),
            ],
        }

    return retrieve_context_v2_node


def _build_policy_summary(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "recommendedAction": str(policy.get("recommendedAction") or ""),
        "difficulty": str(policy.get("difficulty") or ""),
        "shouldExplainBeforeAsk": bool(policy.get("shouldExplainBeforeAsk")),
        "shouldSwitchTopic": bool(policy.get("shouldSwitchTopic")),
        "shouldAskUserChoice": bool(policy.get("shouldAskUserChoice")),
        "requiresHumanReview": bool(policy.get("requiresHumanReview")),
        "policyReasons": list(policy.get("policyReasons") or [])[:3],
        "triggerRules": list(policy.get("triggerRules") or []),
    }


def apply_policy_node(state: dict[str, Any]) -> dict[str, Any]:
    policy_state = {
        "agentMode": state.get("agentMode", "interview"),
        "answerAnalysis": state.get("answerAnalysis") or {},
        "retrievalQuality": state.get("retrievalQuality") or {},
        "weaknessStrategy": state.get("weaknessStrategy") or {},
        "candidateTrainingTasks": state.get("candidateTrainingTasks") or [],
        "history": state.get("history") or [],
    }
    policy = apply_agent_policy(policy_state)
    policy_summary = _build_policy_summary(policy)
    return {
        "policy": policy,
        "policySummary": policy_summary,
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="apply_policy",
                input_summary={
                    "agentMode": policy_state["agentMode"],
                    "weakAnswerStreak": (policy_state["answerAnalysis"] or {}).get("weakAnswerStreak", 0),
                    "repeatedQuestionCount": (policy_state["answerAnalysis"] or {}).get("repeatedQuestionCount", 0),
                },
                output_summary=policy_summary,
            ),
        ],
    }


def select_action_node(state: dict[str, Any]) -> dict[str, Any]:
    analysis = dict(state.get("answerAnalysis") or {})
    policy = dict(state.get("policy") or {})
    answer_status = str(analysis.get("answerStatus") or "模糊")
    next_action = str(policy.get("recommendedAction") or ("lower_difficulty" if answer_status == "不会" else "deep_follow_up"))
    difficulty = str(policy.get("difficulty") or ("basic" if next_action == "lower_difficulty" else "medium"))
    decision = {
        "nextAction": next_action,
        "stage": state.get("nextStage") or "综合追问",
        "difficulty": difficulty,
        "focus": "RAG 与 Agent 基础理解",
        "reason": "LangGraph POC 根据回答状态选择下一步动作。",
        "tools": [
            "retrieve_role_knowledge",
            "retrieve_question_bank",
            "retrieve_candidate_memory",
        ],
        "fallbackUsed": False,
        "policy": policy,
    }
    return {
        "decision": decision,
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="select_action",
                input_summary={"answerStatus": answer_status},
                output_summary={
                    "nextAction": next_action,
                    "difficulty": difficulty,
                    "focus": decision["focus"],
                },
            ),
        ],
    }


def make_select_action_v2_node(decide_action_fn):
    async def select_action_v2_node(state: dict[str, Any]) -> dict[str, Any]:
        result = await decide_action_fn(
            profile=dict(state.get("profile") or {}),
            history=list(state.get("history") or []),
            next_stage=str(state.get("nextStage") or ""),
            agent_mode=str(state.get("agentMode") or "interview"),
            role_hits=list(state.get("roleHits") or []),
            question_hits=list(state.get("questionHits") or []),
            memory_hits=list(state.get("memoryHits") or []),
        )
        decision = dict(result.get("decision") or {})
        agent_state = dict(result.get("agentState") or {})
        policy = dict(state.get("policy") or decision.get("policy") or agent_state.get("policy") or {})
        if policy:
            decision["policy"] = policy
            decision.setdefault("policySummary", _build_policy_summary(policy))
        return {
            "decision": decision,
            "agentState": agent_state,
            "nodeTrace": [
                *_trace_list(state),
                build_node_trace(
                    node_name="select_action",
                    input_summary={"answerStatus": agent_state.get("answerStatus", "")},
                    output_summary={
                        "nextAction": decision.get("nextAction", ""),
                        "difficulty": decision.get("difficulty", ""),
                        "focus": decision.get("focus", ""),
                    },
                    fallback_used=bool(decision.get("fallbackUsed")),
                ),
            ],
        }

    return select_action_v2_node


def generate_question_node(state: dict[str, Any]) -> dict[str, Any]:
    decision = dict(state.get("decision") or {})
    prompt = "我们先把难度降下来：你能用自己的话解释 RAG 为什么需要检索、重排和引用来源吗？"
    if decision.get("nextAction") == "deep_follow_up":
        prompt = "你刚才的回答比较完整，继续追问：如果 RAG 召回结果质量差，你会怎么定位问题？"
    next_question = {
        "stage": decision.get("stage") or state.get("nextStage") or "综合追问",
        "focus": decision.get("focus") or "RAG 与 Agent 基础理解",
        "stability": "stable",
        "prompt": prompt,
    }
    return {
        "nextQuestion": next_question,
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="generate_question",
                input_summary={"nextAction": decision.get("nextAction", "")},
                output_summary={
                    "stage": next_question["stage"],
                    "focus": next_question["focus"],
                },
            ),
        ],
    }


def update_memory_node(state: dict[str, Any]) -> dict[str, Any]:
    memory_update = {
        "status": "deferred",
        "reason": "LangGraph POC 只记录记忆更新意图，不直接写入候选人画像。",
        "weakSignals": (state.get("answerAnalysis") or {}).get("triggerSignals", []),
    }
    return {
        "memoryUpdate": memory_update,
        "nodeTrace": [
            *_trace_list(state),
            build_node_trace(
                node_name="update_memory",
                input_summary={"hasNextQuestion": bool(state.get("nextQuestion"))},
                output_summary={"status": memory_update["status"]},
            ),
        ],
    }
