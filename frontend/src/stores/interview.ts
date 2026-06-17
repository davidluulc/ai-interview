import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as interviewApi from "@/api/interview";

export interface ChatMessage {
  role: "interviewer" | "candidate";
  content: string;
}

export interface SubmitAnswerOptions {
  applicationProfileId?: number;
  agentMode?: interviewApi.AgentMode;
  agentRuntime?: interviewApi.AgentRuntime;
  profile?: Record<string, unknown>;
}

export type InterviewDifficulty = "basic" | "standard" | "pressure";
export type InterviewFocusArea = "project_deep_dive" | "technical_basic" | "rag_agent" | "behavioral" | "mixed";

export interface InterviewSessionConfig {
  totalRounds: number;
  difficulty: InterviewDifficulty;
  focusArea: InterviewFocusArea;
}

const openingQuestion = "请选择投递档案，然后开始一次模拟面试。";

function pickQuestion(response: interviewApi.NextQuestionResponse): string {
  return response.prompt || response.nextQuestion || response.question || "我会基于你的回答继续追问。";
}

export const useInterviewStore = defineStore("interview", () => {
  const messages = ref<ChatMessage[]>([{ role: "interviewer", content: openingQuestion }]);
  const answeredHistory = ref<interviewApi.InterviewHistoryItem[]>([]);
  const draft = ref("");
  const loading = ref(false);
  const error = ref("");
  const decisionSummary = ref("");
  const ragReasons = ref<string[]>([]);
  const agentMode = ref<interviewApi.AgentMode>("coach");
  const agentRuntime = ref<interviewApi.AgentRuntime>("langgraph_mainline");
  const lastRuntimeAudit = ref<interviewApi.RuntimeAuditSummary | null>(null);
  const lastWorkflowTrace = ref<interviewApi.WorkflowTraceItem[]>([]);
  const lastCheckpointSummary = ref<Record<string, unknown> | null>(null);
  const lastFallbackSummary = ref<{ used?: boolean; reason?: string } | null>(null);
  const sessionConfig = ref<InterviewSessionConfig>({
    totalRounds: 8,
    difficulty: "standard",
    focusArea: "mixed"
  });

  const currentRound = computed(() => {
    return Math.min(answeredHistory.value.length + 1, sessionConfig.value.totalRounds);
  });

  const isSessionComplete = computed(() => {
    return answeredHistory.value.length >= sessionConfig.value.totalRounds;
  });

  const canFinish = computed(() => answeredHistory.value.length > 0);

  function setAgentMode(mode: interviewApi.AgentMode): void {
    agentMode.value = mode;
  }

  function setAgentRuntime(runtime: interviewApi.AgentRuntime): void {
    agentRuntime.value = runtime;
  }

  function updateSessionConfig(config: Partial<InterviewSessionConfig>): void {
    sessionConfig.value = {
      ...sessionConfig.value,
      ...config,
      totalRounds: Number(config.totalRounds || sessionConfig.value.totalRounds)
    };
  }

  function resetSession(): void {
    messages.value = [{ role: "interviewer", content: openingQuestion }];
    answeredHistory.value = [];
    draft.value = "";
    error.value = "";
    decisionSummary.value = "";
    ragReasons.value = [];
    lastRuntimeAudit.value = null;
    lastWorkflowTrace.value = [];
    lastCheckpointSummary.value = null;
    lastFallbackSummary.value = null;
  }

  async function submitAnswer(options: SubmitAnswerOptions = {}): Promise<void> {
    const answer = draft.value.trim();
    if (!answer) {
      return;
    }

    const lastQuestion =
      [...messages.value].reverse().find((message) => message.role === "interviewer")?.content || openingQuestion;
    const nextHistory = [...answeredHistory.value, { question: lastQuestion, answer }];

    messages.value.push({ role: "candidate", content: answer });
    draft.value = "";
    loading.value = true;
    error.value = "";

    try {
      const response = await interviewApi.nextQuestion({
        applicationProfileId: options.applicationProfileId,
        agentMode: options.agentMode || agentMode.value,
        agentRuntime: options.agentRuntime || agentRuntime.value,
        profile: options.profile || {},
        history: nextHistory
      });
      const question = pickQuestion(response);
      answeredHistory.value = nextHistory;
      messages.value.push({ role: "interviewer", content: question });
      decisionSummary.value = response.decisionSummary || "";
      ragReasons.value = response.ragReasons || [];
      lastRuntimeAudit.value = response.runtimeAudit || null;
      lastWorkflowTrace.value = response.workflowTrace || [];
      lastCheckpointSummary.value = response.checkpointSummary || null;
      lastFallbackSummary.value = response.fallbackSummary || null;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "生成下一题失败";
    } finally {
      loading.value = false;
    }
  }

  return {
    messages,
    answeredHistory,
    draft,
    loading,
    error,
    decisionSummary,
    ragReasons,
    agentMode,
    agentRuntime,
    lastRuntimeAudit,
    lastWorkflowTrace,
    lastCheckpointSummary,
    lastFallbackSummary,
    sessionConfig,
    currentRound,
    isSessionComplete,
    canFinish,
    setAgentMode,
    setAgentRuntime,
    updateSessionConfig,
    resetSession,
    submitAnswer
  };
});
