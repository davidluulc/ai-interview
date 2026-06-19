import { apiRequest } from "./client";

export type AgentMode = "coach" | "interview";
export type AgentRuntime = "langgraph_mainline" | "classic" | "shadow" | "langgraph_canary";

export interface RuntimeAuditSummary {
  visibleRuntime?: string;
  fallbackUsed?: boolean;
  fallbackReason?: string;
  qualityGateReasons?: string[];
}

export interface WorkflowTraceItem {
  nodeName?: string;
  node?: string;
  inputSummary?: Record<string, unknown>;
  outputSummary?: Record<string, unknown>;
  fallbackUsed?: boolean;
}

export interface InterviewHistoryItem {
  question: string;
  answer: string;
}

export interface NextQuestionPayload {
  applicationProfileId?: number;
  profile?: Record<string, unknown>;
  history?: InterviewHistoryItem[];
  nextStage?: string;
  agentMode?: AgentMode;
  agentRuntime?: AgentRuntime;
}

export interface NextQuestionResponse {
  stage?: string;
  stability?: string;
  focus?: string;
  prompt?: string;
  question?: string;
  nextQuestion?: string;
  decisionSummary?: string;
  agentDecision?: unknown;
  ragReasons?: string[];
  runtimeAudit?: RuntimeAuditSummary;
  workflowTrace?: WorkflowTraceItem[];
  checkpointSummary?: Record<string, unknown>;
  qualityGate?: Record<string, unknown>;
  fallbackSummary?: { used?: boolean; reason?: string };
}

export interface GenerateReportPayload {
  applicationProfileId?: number | null;
  profile?: Record<string, unknown>;
  answers?: InterviewHistoryItem[];
}

export interface ReportResponse extends Record<string, unknown> {
  score: number;
  strengths: string[];
  risks: string[];
  actions: string[];
  questionReviews?: Record<string, unknown>[];
  trainingPlan?: Record<string, unknown>;
}

export async function nextQuestion(payload: NextQuestionPayload): Promise<NextQuestionResponse> {
  return apiRequest<NextQuestionResponse>("/api/interview/next-question", {
    method: "POST",
    body: JSON.stringify({
      profile: payload.profile || {},
      history: payload.history || [],
      nextStage: payload.nextStage || "",
      agentMode: payload.agentMode || "coach",
      agentRuntime: payload.agentRuntime || "langgraph_mainline",
      applicationProfileId: payload.applicationProfileId
    })
  });
}

export async function generateReport(payload: GenerateReportPayload): Promise<ReportResponse> {
  return apiRequest<ReportResponse>("/api/interview/report", {
    method: "POST",
    body: JSON.stringify({
      applicationProfileId: payload.applicationProfileId,
      profile: payload.profile || {},
      answers: payload.answers || []
    })
  });
}
