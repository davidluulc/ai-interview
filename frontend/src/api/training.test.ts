import { beforeEach, describe, expect, it, vi } from "vitest";
import { completeTrainingTask, getTrainingPractice } from "./training";

describe("training api", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("loads a training practice payload", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        task: {
          id: 1,
          weakTag: "rag_quality",
          title: "RAG",
          description: "",
          status: "todo",
          priority: "high",
          masteryScore: 45
        },
        practice: {
          weakTag: "rag_quality",
          question: "什么是 Hit@K？",
          answerKeyPoints: ["Hit@K"],
          commonMistakes: [],
          rubric: []
        }
      })
    );

    await getTrainingPractice(1, "coach", "basic");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/training/tasks/1/practice?mode=coach&difficulty=basic",
      expect.any(Object)
    );
  });

  it("completes a task with practice answer payload", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ id: 1 }));

    await completeTrainingTask(1, {
      answerStatus: "完整",
      answerText: "我的回答",
      selfRating: 4
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/training/tasks/1/complete",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ answerStatus: "完整", answerText: "我的回答", selfRating: 4 })
      })
    );
  });
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" }
  });
}
