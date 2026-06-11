from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend_python.candidate_memory import retrieve_candidate_memory
from backend_python.database import SessionLocal
from backend_python.langgraph_agent.adapters import decide_real_action_for_graph, retrieve_real_context_for_graph
from backend_python.langgraph_agent.checkpoint import summarize_checkpoint
from backend_python.langgraph_agent.graph import run_interview_graph_poc
from backend_python.langgraph_agent.service import run_langgraph_agent_v2
from backend_python.llm_client import call_model
from backend_python.question_rag import retrieve_questions
from backend_python.rag import retrieve_role_context


router = APIRouter(prefix="/api/langgraph-agent", tags=["langgraph-agent"])


class LangGraphQuestionRequest(BaseModel):
    threadId: str = "default-thread"
    applicationProfileId: int | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)
    nextStage: str = ""
    agentMode: str = "interview"
    useRealRag: bool = False
    useRealDecision: bool = False


@router.post("/next-question-poc")
async def next_question_poc(payload: LangGraphQuestionRequest) -> dict[str, Any]:
    result = run_interview_graph_poc(
        profile=payload.profile,
        history=payload.history,
        next_stage=payload.nextStage,
        agent_mode=payload.agentMode,
    )
    return {
        "graphState": result,
        "nodeTrace": result.get("nodeTrace", []),
        "toolCalls": result.get("toolCalls", []),
        "decision": result.get("decision", {}),
        "nextQuestion": result.get("nextQuestion", {}),
        "memoryUpdate": result.get("memoryUpdate", {}),
    }


def _fake_retrieve_context(profile: dict[str, Any], next_stage: str) -> dict[str, Any]:
    target_role = str(profile.get("targetRole") or "AI 应用开发")
    role_hits = [{"id": "role-v2-fake-1", "content": f"{target_role} 需要理解 RAG、Agent 和 checkpoint。"}]
    question_hits = [{"id": "question-v2-fake-1", "content": "请解释 LangGraph checkpoint 的作用。"}]
    memory_hits = [{"id": "memory-v2-fake-1", "content": "候选人正在学习 LangGraph 迁移路线。"}]
    return {
        "roleHits": role_hits,
        "questionHits": question_hits,
        "memoryHits": memory_hits,
        "toolCalls": [
            {"toolName": "retrieve_role_knowledge", "success": True},
            {"toolName": "retrieve_question_bank", "success": True},
            {"toolName": "retrieve_candidate_memory", "success": True},
        ],
        "retrievalQuality": {
            "roleKnowledge": {"level": "good", "hitCount": len(role_hits)},
            "questionBank": {"level": "good", "hitCount": len(question_hits)},
            "candidateMemory": {"level": "good", "hitCount": len(memory_hits)},
        },
    }


async def _fake_decide_action(**kwargs: Any) -> dict[str, Any]:
    history = list(kwargs.get("history") or [])
    last_answer = str((history[-1] if history else {}).get("answer") or "")
    weak_answer = not last_answer.strip() or "不知道" in last_answer or "不会" in last_answer
    next_action = "lower_difficulty" if weak_answer else "deep_follow_up"
    difficulty = "basic" if weak_answer else "medium"
    decision = {
        "nextAction": next_action,
        "stage": str(kwargs.get("next_stage") or "综合追问"),
        "difficulty": difficulty,
        "focus": "LangGraph checkpoint 与 RAG 协作",
        "reason": "V2 实验接口使用 fake decision 保持测试稳定。",
        "tools": ["retrieve_context", "analyze_answer"],
        "fallbackUsed": False,
        "decisionSummary": f"LangGraph V2：{next_action}。V2 实验接口使用 fake decision 保持测试稳定。",
    }
    return {"decision": decision, "agentState": {"answerStatus": "不会" if weak_answer else "完整"}}


def _real_retrieve_context(profile: dict[str, Any], next_stage: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        return retrieve_real_context_for_graph(
            profile=profile,
            next_stage=next_stage,
            role_retrieve_fn=retrieve_role_context,
            question_retrieve_fn=retrieve_questions,
            memory_retrieve_fn=lambda profile, limit: retrieve_candidate_memory(db, profile, limit=limit),
            role_retrieve_kwargs={"db": db},
            question_retrieve_kwargs={"db": db},
        )
    finally:
        db.close()


async def _real_decide_action(**kwargs: Any) -> dict[str, Any]:
    return await decide_real_action_for_graph(call_model_fn=call_model, **kwargs)


@router.post("/next-question-v2")
async def next_question_v2(payload: LangGraphQuestionRequest) -> dict[str, Any]:
    result = await run_langgraph_agent_v2(
        thread_id=payload.threadId,
        application_profile_id=payload.applicationProfileId,
        profile=payload.profile,
        history=payload.history,
        next_stage=payload.nextStage,
        agent_mode=payload.agentMode,
        use_real_rag=payload.useRealRag,
        use_real_decision=payload.useRealDecision,
        retrieve_context_fn=_real_retrieve_context if payload.useRealRag else _fake_retrieve_context,
        decide_action_fn=_real_decide_action if payload.useRealDecision else _fake_decide_action,
    )
    return {
        "threadId": result.get("threadId", payload.threadId),
        "graphState": result,
        "nodeTrace": result.get("nodeTrace", []),
        "toolCalls": result.get("toolCalls", []),
        "decision": result.get("decision", {}),
        "nextQuestion": result.get("nextQuestion", {}),
        "memoryUpdate": result.get("memoryUpdate", {}),
        "checkpointSummary": result.get("checkpointSummary", {}),
    }


@router.get("/checkpoint/{thread_id}")
async def checkpoint_summary(thread_id: str) -> dict[str, Any]:
    return summarize_checkpoint(thread_id)
