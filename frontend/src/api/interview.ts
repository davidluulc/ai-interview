import { apiRequest } from "./client";

export type AgentMode = "coach" | "interview";

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
}

export async function nextQuestion(payload: NextQuestionPayload): Promise<NextQuestionResponse> {
  return apiRequest<NextQuestionResponse>("/api/interview/next-question", {
    method: "POST",
    body: JSON.stringify({
      profile: payload.profile || {},
      history: payload.history || [],
      nextStage: payload.nextStage || "",
      agentMode: payload.agentMode || "coach",
      applicationProfileId: payload.applicationProfileId
    })
  });
}
