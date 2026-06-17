from __future__ import annotations

from copy import deepcopy
from typing import Any


def normalize_thread_id(thread_id: str) -> str:
    return str(thread_id or "default-thread").strip() or "default-thread"


def empty_checkpoint_summary(thread_id: str) -> dict[str, Any]:
    safe_thread_id = normalize_thread_id(thread_id)
    return {
        "enabled": True,
        "exists": False,
        "threadId": safe_thread_id,
        "runtime": "",
        "status": "missing",
        "currentNode": "",
        "roundCount": 0,
        "lastAction": "",
        "lastQuestion": "",
        "nodeTraceCount": 0,
        "stateKeys": [],
        "policyRecommendedAction": "",
        "shouldAskUserChoice": False,
        "requiresHumanReview": False,
        "policyReasons": [],
        "policyTriggerRules": [],
        "interrupt": None,
        "resumeDecision": "",
        "runtimeTrace": [],
    }


def build_checkpoint_summary(*, thread_id: str, state: dict[str, Any]) -> dict[str, Any]:
    safe_thread_id = normalize_thread_id(thread_id)
    node_trace = state.get("nodeTrace") if isinstance(state.get("nodeTrace"), list) else []
    decision = state.get("decision") if isinstance(state.get("decision"), dict) else {}
    policy = state.get("policy") if isinstance(state.get("policy"), dict) else {}
    next_question = state.get("nextQuestion") if isinstance(state.get("nextQuestion"), dict) else {}
    runtime_trace = state.get("runtimeTrace") if isinstance(state.get("runtimeTrace"), list) else []
    return {
        "enabled": True,
        "exists": True,
        "threadId": safe_thread_id,
        "runtime": str(state.get("runtime") or state.get("agentRuntime") or ""),
        "status": str(state.get("status") or "completed"),
        "currentNode": str(state.get("currentNode") or ""),
        "roundCount": int(state.get("roundCount") or 0),
        "lastAction": str(decision.get("nextAction") or policy.get("recommendedAction") or ""),
        "lastQuestion": str(next_question.get("prompt") or next_question.get("content") or ""),
        "nodeTraceCount": len(node_trace),
        "stateKeys": sorted(str(key) for key in state.keys()),
        "policyRecommendedAction": str(policy.get("recommendedAction") or ""),
        "shouldAskUserChoice": bool(policy.get("shouldAskUserChoice")),
        "requiresHumanReview": bool(policy.get("requiresHumanReview")),
        "policyReasons": list(policy.get("policyReasons") or [])[:5],
        "policyTriggerRules": list(policy.get("triggerRules") or []),
        "interrupt": state.get("interrupt") if isinstance(state.get("interrupt"), dict) else None,
        "resumeDecision": str(state.get("resumeDecision") or ""),
        "runtimeTrace": runtime_trace,
    }


class InMemoryCheckpointSummaryStore:
    def __init__(self) -> None:
        self._summaries: dict[str, dict[str, Any]] = {}

    def save_summary(self, summary: dict[str, Any]) -> dict[str, Any]:
        thread_id = normalize_thread_id(str(summary.get("threadId") or ""))
        stored = deepcopy(summary)
        stored["threadId"] = thread_id
        stored["exists"] = True
        self._summaries[thread_id] = stored
        return deepcopy(stored)

    def get_summary(self, thread_id: str) -> dict[str, Any]:
        safe_thread_id = normalize_thread_id(thread_id)
        if safe_thread_id not in self._summaries:
            return empty_checkpoint_summary(safe_thread_id)
        return deepcopy(self._summaries[safe_thread_id])

    def list_thread_runs(self, thread_id: str) -> list[dict[str, Any]]:
        summary = self.get_summary(thread_id)
        return [] if not summary.get("exists") else [summary]

    def mark_interrupted(self, thread_id: str, *, interrupt: dict[str, Any]) -> dict[str, Any]:
        summary = self.get_summary(thread_id)
        summary["exists"] = True
        summary["status"] = "interrupted"
        summary["currentNode"] = str(summary.get("currentNode") or "human_review")
        summary["requiresHumanReview"] = True
        summary["interrupt"] = deepcopy(interrupt)
        return self.save_summary(summary)

    def mark_resumed(self, thread_id: str, *, resume_decision: str) -> dict[str, Any]:
        summary = self.get_summary(thread_id)
        summary["exists"] = True
        summary["status"] = "resumed"
        summary["resumeDecision"] = str(resume_decision or "")
        summary["interrupt"] = None
        return self.save_summary(summary)


checkpoint_summary_store = InMemoryCheckpointSummaryStore()
