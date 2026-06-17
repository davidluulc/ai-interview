import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as historyApi from "@/api/history";
import { useHistoryStore } from "./history";

vi.mock("@/api/history", () => ({
  listHistory: vi.fn()
}));

describe("history store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(historyApi.listHistory).mockReset();
  });

  it("loads interview history records for the current user", async () => {
    vi.mocked(historyApi.listHistory).mockResolvedValue([
      {
        id: 1,
        createdAt: "2026-06-12T10:00:00",
        applicationProfile: {
          id: 2,
          title: "AI 应用开发投递",
          targetRole: "AI 应用开发实习生"
        },
        profile: { targetRole: "AI 应用开发实习生" },
        answers: [{ question: "什么是 RAG？", answer: "检索增强生成。" }],
        report: { score: 82, level: "良好", weakTags: ["rag_quality"] }
      }
    ]);

    const store = useHistoryStore();
    await store.loadHistory();

    expect(store.items).toHaveLength(1);
    expect(store.items[0].applicationProfile?.title).toBe("AI 应用开发投递");
    expect(store.latestItems).toHaveLength(1);
    expect(store.findById(1)?.report.score).toBe(82);
    expect(store.loading).toBe(false);
    expect(store.error).toBe("");
  });

  it("records a readable error when history loading fails", async () => {
    vi.mocked(historyApi.listHistory).mockRejectedValue(new Error("登录已过期"));

    const store = useHistoryStore();
    await store.loadHistory();

    expect(store.items).toEqual([]);
    expect(store.error).toBe("登录已过期");
    expect(store.loading).toBe(false);
  });

  it("filters records by application profile, role keyword and sort order", async () => {
    vi.mocked(historyApi.listHistory).mockResolvedValue([
      {
        id: 1,
        createdAt: "2026-06-12T10:00:00",
        applicationProfile: { id: 2, title: "AI 应用开发投递", targetRole: "AI 应用开发实习生" },
        profile: { targetRole: "AI 应用开发实习生" },
        answers: [],
        report: { score: 82 }
      },
      {
        id: 2,
        createdAt: "2026-06-11T10:00:00",
        applicationProfile: { id: 3, title: "后端实习投递", targetRole: "Python 后端开发实习生" },
        profile: { targetRole: "Python 后端开发实习生" },
        answers: [],
        report: { score: 76 }
      },
      {
        id: 3,
        createdAt: "2026-06-10T10:00:00",
        applicationProfile: { id: 2, title: "AI 应用开发投递", targetRole: "AI 应用开发实习生" },
        profile: { targetRole: "AI 应用开发实习生" },
        answers: [],
        report: { score: 68 }
      }
    ]);

    const store = useHistoryStore();
    await store.loadHistory();

    expect(store.profileOptions).toEqual([
      { id: 2, title: "AI 应用开发投递" },
      { id: 3, title: "后端实习投递" }
    ]);

    store.setFilters({ applicationProfileId: 2, roleKeyword: "AI", sortOrder: "oldest" });

    expect(store.filteredItems.map((item) => item.id)).toEqual([3, 1]);
  });
});
