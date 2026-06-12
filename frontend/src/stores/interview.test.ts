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

  it("sends the latest question and answer as backend history", async () => {
    vi.mocked(interviewApi.nextQuestion).mockResolvedValue({
      prompt: "你能继续讲讲 FastAPI 的 Depends 吗？",
      decisionSummary: "上一轮回答提到了依赖注入，因此继续追问。"
    });

    const store = useInterviewStore();
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
            question: "请选择投递档案，然后开始一次模拟面试。",
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
});
