import { defineStore } from "pinia";
import { ref } from "vue";
import * as interviewApi from "@/api/interview";

export interface ChatMessage {
  role: "interviewer" | "candidate";
  content: string;
}

export interface SubmitAnswerOptions {
  applicationProfileId?: number;
  agentMode?: interviewApi.AgentMode;
  profile?: Record<string, unknown>;
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
        agentMode: options.agentMode || "coach",
        profile: options.profile || {},
        history: nextHistory
      });
      const question = pickQuestion(response);
      answeredHistory.value = nextHistory;
      messages.value.push({ role: "interviewer", content: question });
      decisionSummary.value = response.decisionSummary || "";
      ragReasons.value = response.ragReasons || [];
    } catch (err) {
      error.value = err instanceof Error ? err.message : "生成下一题失败";
    } finally {
      loading.value = false;
    }
  }

  return { messages, draft, loading, error, decisionSummary, ragReasons, submitAnswer };
});
