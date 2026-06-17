from typing import Any

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    applicationProfileId: int | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)
    nextStage: str = ""
    agentMode: str = "interview"
    agentRuntime: str | None = Field(
        default=None,
        description="Agent runtime preference: langgraph_mainline, classic, shadow, or langgraph_canary",
    )


class ReportRequest(BaseModel):
    applicationProfileId: int | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    answers: list[dict[str, Any]] = Field(default_factory=list)


class PositionMatchRequest(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)
    targetDirection: str = ""


class QuestionResponse(BaseModel):
    stage: str
    stability: str
    focus: str = ""
    prompt: str
    agentDecision: dict[str, Any] = Field(default_factory=dict)
    decisionSummary: str = ""
    ragReasons: list[str] = Field(default_factory=list)
    runtimeAudit: dict[str, Any] = Field(default_factory=dict)
    workflowTrace: list[dict[str, Any]] = Field(default_factory=list)
    checkpointSummary: dict[str, Any] = Field(default_factory=dict)
    qualityGate: dict[str, Any] = Field(default_factory=dict)
    fallbackSummary: dict[str, Any] = Field(default_factory=dict)


class ReportResponse(BaseModel):
    score: int
    strengths: list[str]
    risks: list[str]
    actions: list[str]
    questionReviews: list[dict[str, Any]] = Field(default_factory=list)
    trainingPlan: dict[str, Any] = Field(default_factory=dict)


class HistoryCreateRequest(BaseModel):
    applicationProfileId: int | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    answers: list[dict[str, Any]] = Field(default_factory=list)
    report: dict[str, Any] = Field(default_factory=dict)


class HistoryItemResponse(BaseModel):
    id: int
    createdAt: str
    applicationProfile: dict[str, Any] | None = None
    profile: dict[str, Any]
    answers: list[dict[str, Any]]
    report: dict[str, Any]
