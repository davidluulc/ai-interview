from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend_python.candidate_memory import retrieve_candidate_memory
from backend_python.database import SessionLocal, get_db
from backend_python.human_review_policy import evaluate_human_review
from backend_python.langgraph_agent.adapters import decide_real_action_for_graph, retrieve_real_context_for_graph
from backend_python.langgraph_agent.checkpoint import record_checkpoint_summary, summarize_checkpoint
from backend_python.langgraph_agent.checkpoint_persistence import (
    get_latest_checkpoint_summary,
    list_checkpoint_summaries,
    list_latest_checkpoint_summaries,
    save_checkpoint_summary,
)
from backend_python.langgraph_agent.checkpoint_store import checkpoint_summary_store
from backend_python.langgraph_agent.graph import run_interview_graph_poc
from backend_python.langgraph_agent.replay import build_runtime_replay
from backend_python.langgraph_agent.review_queue import build_review_queue, validate_review_decision
from backend_python.langgraph_agent.runtime_report import build_runtime_report
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


class LangGraphRuntimeRunRequest(BaseModel):
    threadId: str = "default-thread"
    agentRuntime: str = "langgraph"
    agentMode: str = "interview"
    applicationProfileId: int | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)
    answer: str = ""
    nextStage: str = ""
    enableInterrupt: bool = False


class LangGraphRuntimeResumeRequest(BaseModel):
    threadId: str
    decision: str
    comment: str = ""


class LangGraphReviewResolveRequest(BaseModel):
    decision: str
    comment: str = ""


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
async def checkpoint_summary(thread_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    persisted = get_latest_checkpoint_summary(db, thread_id)
    return persisted if persisted.get("exists") else summarize_checkpoint(thread_id)


def _weak_answer_streak(history: list[dict[str, Any]], answer: str) -> int:
    answers = [str(item.get("answer") or "") for item in history]
    if answer:
        answers.append(answer)

    streak = 0
    for value in reversed(answers):
        normalized = value.strip()
        if not normalized or "不会" in normalized or "不知道" in normalized:
            streak += 1
            continue
        break
    return streak


@router.post("/runtime/run")
async def runtime_run(payload: LangGraphRuntimeRunRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    weak_streak = _weak_answer_streak(payload.history, payload.answer)
    should_review = weak_streak >= 3
    policy = {
        "requiresHumanReview": should_review,
        "recommendedAction": "lower_difficulty" if weak_streak else "deep_follow_up",
        "triggerRules": ["weak_answer_streak"] if should_review else [],
    }
    review = evaluate_human_review(
        agent_policy=policy,
        answer_analysis={"weakAnswerStreak": weak_streak},
        history=payload.history,
    )
    interrupted = bool(payload.enableInterrupt and review["shouldInterrupt"])
    state = {
        "runtime": payload.agentRuntime,
        "status": "interrupted" if interrupted else "completed",
        "currentNode": "human_review" if interrupted else "generate_question",
        "roundCount": len(payload.history),
        "decision": {"nextAction": policy["recommendedAction"]},
        "policy": policy,
        "interrupt": review if interrupted else None,
        "nodeTrace": [
            {"node": "observe_state"},
            {"node": "human_review" if interrupted else "generate_question"},
        ],
        "runtimeTrace": [{"runtime": payload.agentRuntime, "status": "started"}],
        "nextQuestion": {}
        if interrupted
        else {"content": "请继续解释 LangGraph checkpoint 和 thread_id 的关系。"},
    }
    checkpoint = record_checkpoint_summary(thread_id=payload.threadId, state=state)

    if interrupted:
        checkpoint = checkpoint_summary_store.mark_interrupted(payload.threadId, interrupt=review)
        checkpoint["qualityGate"] = {}
        checkpoint["comparisonSummary"] = {}
        persisted_checkpoint = save_checkpoint_summary(db, checkpoint)
        return {
            "threadId": payload.threadId,
            "runtime": payload.agentRuntime,
            "status": "interrupted",
            "question": None,
            "decision": state["decision"],
            "interrupt": review,
            "checkpointSummary": persisted_checkpoint,
            "runtimeTrace": state["runtimeTrace"],
        }

    checkpoint["qualityGate"] = {}
    checkpoint["comparisonSummary"] = {}
    persisted_checkpoint = save_checkpoint_summary(db, checkpoint)
    return {
        "threadId": payload.threadId,
        "runtime": payload.agentRuntime,
        "status": "completed",
        "question": state["nextQuestion"],
        "decision": state["decision"],
        "interrupt": None,
        "checkpointSummary": persisted_checkpoint,
        "runtimeTrace": state["runtimeTrace"],
    }


@router.get("/runtime/runs/{thread_id}")
async def runtime_runs(thread_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    return {
        "threadId": thread_id,
        "items": list_checkpoint_summaries(db, thread_id),
    }


@router.get("/runtime/replay/{thread_id}")
async def runtime_replay(thread_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    persisted = get_latest_checkpoint_summary(db, thread_id)
    return build_runtime_replay(persisted)


@router.get("/runtime/report/{thread_id}")
async def runtime_report(thread_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    return build_runtime_report(thread_id, list_checkpoint_summaries(db, thread_id))


@router.get("/runtime/reviews")
async def runtime_reviews(db: Session = Depends(get_db)) -> dict[str, Any]:
    return {"items": build_review_queue(list_latest_checkpoint_summaries(db))}


@router.post("/runtime/reviews/{thread_id}/resolve")
async def runtime_review_resolve(
    thread_id: str,
    payload: LangGraphReviewResolveRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        decision = validate_review_decision(payload.decision)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    checkpoint = summarize_checkpoint(thread_id)
    if not checkpoint.get("exists"):
        raise HTTPException(status_code=404, detail="LangGraph runtime thread not found")
    if checkpoint.get("status") != "interrupted" and not checkpoint.get("requiresHumanReview"):
        raise HTTPException(status_code=400, detail="LangGraph runtime thread does not require human review")

    resumed = checkpoint_summary_store.mark_resumed(thread_id, resume_decision=decision)
    resumed["requiresHumanReview"] = False
    resumed["currentNode"] = "generate_question" if decision != "end_interview" else "end_interview"
    resumed["interrupt"] = None
    persisted_checkpoint = save_checkpoint_summary(db, resumed)
    return {
        "threadId": thread_id,
        "runtime": persisted_checkpoint.get("runtime") or "langgraph",
        "status": persisted_checkpoint.get("status") or "resumed",
        "resumeDecision": decision,
        "comment": payload.comment,
        "checkpointSummary": persisted_checkpoint,
    }


@router.post("/runtime/resume")
async def runtime_resume(payload: LangGraphRuntimeResumeRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    checkpoint = summarize_checkpoint(payload.threadId)
    if not checkpoint.get("exists"):
        raise HTTPException(status_code=404, detail="LangGraph runtime thread not found")
    if checkpoint.get("status") != "interrupted":
        raise HTTPException(status_code=400, detail="LangGraph runtime thread is not interrupted")

    resumed = checkpoint_summary_store.mark_resumed(payload.threadId, resume_decision=payload.decision)
    persisted_checkpoint = save_checkpoint_summary(db, resumed)
    question = {
        "content": "根据人工选择，系统将继续生成下一轮面试问题。"
        if payload.decision == "continue_interview"
        else "根据人工选择，系统先切换到学习辅导模式，拆解当前知识点。"
    }
    return {
        "threadId": payload.threadId,
        "runtime": resumed.get("runtime") or "langgraph",
        "status": "completed",
        "question": question,
        "resumeDecision": payload.decision,
        "checkpointSummary": persisted_checkpoint,
        "runtimeTrace": persisted_checkpoint.get("runtimeTrace", []),
    }
