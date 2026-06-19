import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as interviewApi from "@/api/interview";
import { useInterviewStore } from "./interview";

vi.mock("@/api/interview", () => ({
  nextQuestion: vi.fn()
}));

describe("interview store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(interviewApi.nextQuestion).mockReset();
  });

  function makeReadySession(store: ReturnType<typeof useInterviewStore>, question = "请解释 FastAPI Depends。"): void {
    store.messages = [{ role: "interviewer", content: question }];
    store.sessionStatus = "ready";
  }

  it("uses coach mode by default and supports switching to interview mode", () => {
    const store = useInterviewStore();

    expect(store.agentMode).toBe("coach");

    store.setAgentMode("interview");

    expect(store.agentMode).toBe("interview");
  });

  it("does not submit the placeholder prompt as answered history before the first backend question", async () => {
    const store = useInterviewStore();
    store.draft = "开始吧";

    await store.submitAnswer({ applicationProfileId: 7, profile: { targetRole: "Python 后端开发实习生" } });

    expect(interviewApi.nextQuestion).not.toHaveBeenCalled();
    expect(store.answeredHistory).toEqual([]);
  });

  it("starts an interview by requesting the first question with empty history", async () => {
    vi.mocked(interviewApi.nextQuestion).mockResolvedValue({
      prompt: "请先介绍你最有代表性的后端项目。"
    });
    const store = useInterviewStore();

    await store.startInterview({
      applicationProfileId: 7,
      profile: { targetRole: "Python 后端开发实习生" },
      agentMode: "coach"
    });

    expect(interviewApi.nextQuestion).toHaveBeenCalledWith(
      expect.objectContaining({
        applicationProfileId: 7,
        agentMode: "coach",
        history: []
      })
    );
    expect(store.answeredHistory).toEqual([]);
    expect(store.messages.at(-1)?.content).toBe("请先介绍你最有代表性的后端项目。");
  });

  it("sends the latest question and answer as backend history", async () => {
    vi.mocked(interviewApi.nextQuestion).mockResolvedValue({
      prompt: "你能继续讲讲 FastAPI 的 Depends 吗？",
      decisionSummary: "上一轮回答提到了依赖注入，因此继续追问。"
    });

    const store = useInterviewStore();
    makeReadySession(store, "请解释 FastAPI Depends。");
    store.draft = "Depends 是依赖注入。";
    await store.submitAnswer({
      applicationProfileId: 7,
      profile: { targetRole: "Python 后端开发实习生" },
      agentMode: "coach"
    });

    expect(interviewApi.nextQuestion).toHaveBeenCalledWith(
      expect.objectContaining({
        applicationProfileId: 7,
        agentMode: "coach",
        profile: { targetRole: "Python 后端开发实习生" },
        history: [
          {
            question: "请解释 FastAPI Depends。",
            answer: "Depends 是依赖注入。"
          }
        ]
      })
    );
    expect(store.messages.at(-1)?.content).toBe("你能继续讲讲 FastAPI 的 Depends 吗？");
    expect(store.decisionSummary).toBe("上一轮回答提到了依赖注入，因此继续追问。");
  });

  it("does not call backend for empty answers", async () => {
    const store = useInterviewStore();
    store.draft = "   ";

    await store.submitAnswer();

    expect(interviewApi.nextQuestion).not.toHaveBeenCalled();
  });

  it("submits answers with the selected agent mode", async () => {
    vi.mocked(interviewApi.nextQuestion).mockResolvedValue({
      prompt: "请继续讲项目里的 RAG 质量评估。"
    });

    const store = useInterviewStore();
    makeReadySession(store, "请讲讲你项目里的 RAG 质量评估。");
    store.draft = "我做了 Hit@K 和 MRR";
    store.setAgentMode("interview");

    await store.submitAnswer({ applicationProfileId: 3, profile: { title: "AI 应用开发投递" } });

    expect(interviewApi.nextQuestion).toHaveBeenCalledWith(
      expect.objectContaining({
        applicationProfileId: 3,
        agentMode: "interview"
      })
    );
  });

  it("tracks agent runtime and sends it with next question requests", async () => {
    vi.mocked(interviewApi.nextQuestion).mockResolvedValue({
      prompt: "请解释 LangGraph 灰度链路为什么需要 fallback。"
    });

    const store = useInterviewStore();
    makeReadySession(store, "请解释 LangGraph 灰度链路为什么需要 fallback。");
    store.draft = "为了保证主链路稳定。";
    store.setAgentRuntime("langgraph_canary");

    await store.submitAnswer({ applicationProfileId: 5, profile: { title: "管理员演示档案" } });

    expect(store.agentRuntime).toBe("langgraph_canary");
    expect(interviewApi.nextQuestion).toHaveBeenCalledWith(
      expect.objectContaining({
        applicationProfileId: 5,
        agentRuntime: "langgraph_canary"
      })
    );
  });

  it("stores runtime summary from next question response", async () => {
    vi.mocked(interviewApi.nextQuestion).mockResolvedValue({
      prompt: "Explain LangGraph mainline.",
      decisionSummary: "Continue around workflow orchestration.",
      ragReasons: [],
      runtimeAudit: {
        visibleRuntime: "langgraph_mainline",
        fallbackUsed: false
      },
      workflowTrace: [{ nodeName: "observe_state" }, { nodeName: "retrieve_context" }],
      checkpointSummary: { exists: true, threadId: "thread-1" },
      fallbackSummary: { used: false, reason: "" }
    });

    const store = useInterviewStore();
    makeReadySession(store, "Explain LangGraph mainline.");
    store.draft = "I know a little about workflow orchestration.";
    await store.submitAnswer({ profile: { targetRole: "AI application developer" } });

    expect(store.lastRuntimeAudit?.visibleRuntime).toBe("langgraph_mainline");
    expect(store.lastWorkflowTrace).toHaveLength(2);
    expect(store.lastCheckpointSummary?.threadId).toBe("thread-1");
    expect(store.lastFallbackSummary?.used).toBe(false);
  });

  it("tracks interview session config and progress", () => {
    const store = useInterviewStore();

    store.updateSessionConfig({
      totalRounds: 8,
      difficulty: "standard",
      focusArea: "rag_agent"
    });

    expect(store.sessionConfig.totalRounds).toBe(8);
    expect(store.sessionConfig.difficulty).toBe("standard");
    expect(store.sessionConfig.focusArea).toBe("rag_agent");
    expect(store.currentRound).toBe(1);
    expect(store.isSessionComplete).toBe(false);
    expect(store.canFinish).toBe(false);
  });

  it("marks a session complete when answered history reaches total rounds", () => {
    const store = useInterviewStore();
    store.updateSessionConfig({ totalRounds: 2 });
    store.answeredHistory = [
      { question: "Q1", answer: "A1" },
      { question: "Q2", answer: "A2" }
    ];

    expect(store.currentRound).toBe(2);
    expect(store.isSessionComplete).toBe(true);
    expect(store.canFinish).toBe(true);
  });

  it("resets interview session state", () => {
    const store = useInterviewStore();
    store.updateSessionConfig({
      totalRounds: 10,
      difficulty: "pressure",
      focusArea: "project_deep_dive"
    });
    store.answeredHistory = [{ question: "Q1", answer: "A1" }];
    store.decisionSummary = "旧决策";
    store.ragReasons = ["旧资料"];

    store.resetSession();

    expect(store.answeredHistory).toEqual([]);
    expect(store.currentRound).toBe(1);
    expect(store.decisionSummary).toBe("");
    expect(store.ragReasons).toEqual([]);
  });
});
