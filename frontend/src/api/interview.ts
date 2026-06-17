import { apiRequest } from "./client";

export type AgentMode = "coach" | "interview";
export type AgentRuntime = "classic" | "shadow" | "langgraph_canary";

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
  runtimeAudit?: Record<string, unknown>;
}

export async function nextQuestion(payload: NextQuestionPayload): Promise<NextQuestionResponse> {
  return apiRequest<NextQuestionResponse>("/api/interview/next-question", {
    method: "POST",
    body: JSON.stringify({
      profile: payload.profile || {},
      history: payload.history || [],
      nextStage: payload.nextStage || "",
      agentMode: payload.agentMode || "coach",
      agentRuntime: payload.agentRuntime || "classic",
      applicationProfileId: payload.applicationProfileId
    })
  });
}
