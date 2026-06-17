import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import HistoryPage from "./HistoryPage.vue";

const push = vi.fn();

const historyStore = {
  items: [
    {
      id: 8,
      createdAt: "2026-06-12T10:00:00",
      applicationProfile: {
        id: 1,
        title: "后端实习投递",
        targetRole: "Python 后端开发实习生"
      },
      profile: { targetRole: "Python 后端开发实习生" },
      answers: [{ question: "请介绍 FastAPI Depends", answer: "它是依赖注入。" }],
      report: { score: 76, level: "可提升", weakTags: ["backend_architecture"] }
    }
  ],
  filteredItems: [
    {
      id: 8,
      createdAt: "2026-06-12T10:00:00",
      applicationProfile: {
        id: 1,
        title: "后端实习投递",
        targetRole: "Python 后端开发实习生"
      },
      profile: { targetRole: "Python 后端开发实习生" },
      answers: [{ question: "请介绍 FastAPI Depends", answer: "它是依赖注入。" }],
      report: { score: 76, level: "可提升", weakTags: ["backend_architecture"] }
    }
  ],
  profileOptions: [{ id: 1, title: "后端实习投递" }],
  applicationProfileId: null as number | null,
  roleKeyword: "",
  sortOrder: "newest",
  loading: false,
  error: "",
  loadHistory: vi.fn(),
  setFilters: vi.fn()
};

vi.mock("vue-router", () => ({
  useRouter: () => ({ push })
}));

vi.mock("@/stores/history", () => ({
  useHistoryStore: () => historyStore
}));

describe("history page", () => {
  beforeEach(() => {
    push.mockReset();
    historyStore.loadHistory.mockReset();
    historyStore.setFilters.mockReset();
    historyStore.filteredItems = [...historyStore.items];
    historyStore.profileOptions = [{ id: 1, title: "后端实习投递" }];
  });

  it("renders history records and opens the report page", async () => {
    const wrapper = mount(HistoryPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(historyStore.loadHistory).toHaveBeenCalled();
    expect(wrapper.text()).toContain("历史复盘");
    expect(wrapper.text()).toContain("后端实习投递");
    expect(wrapper.text()).toContain("Python 后端开发实习生");
    expect(wrapper.text()).toContain("76");
    expect(wrapper.text()).toContain("backend_architecture");

    await wrapper.get('[data-testid="open-report-8"]').trigger("click");
    expect(push).toHaveBeenCalledWith("/vue/app/reports/8");
  });

  it("updates filters from the history filter controls", async () => {
    const wrapper = mount(HistoryPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="history-profile-filter"]').setValue("1");
    expect(historyStore.setFilters).toHaveBeenLastCalledWith({
      applicationProfileId: 1,
      roleKeyword: "",
      sortOrder: "newest"
    });

    await wrapper.get('[data-testid="history-role-filter"]').setValue("后端");
    expect(historyStore.setFilters).toHaveBeenLastCalledWith({
      applicationProfileId: null,
      roleKeyword: "后端",
      sortOrder: "newest"
    });

    await wrapper.get('[data-testid="history-sort-order"]').setValue("oldest");
    expect(historyStore.setFilters).toHaveBeenLastCalledWith({
      applicationProfileId: null,
      roleKeyword: "",
      sortOrder: "oldest"
    });
  });

  it("shows a useful empty state when there are no history records", () => {
    const originalItems = historyStore.items;
    const originalFilteredItems = historyStore.filteredItems;
    historyStore.items = [];
    historyStore.filteredItems = [];

    const wrapper = mount(HistoryPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("还没有面试记录");
    expect(wrapper.text()).toContain("先完成一次模拟面试");

    historyStore.items = originalItems;
    historyStore.filteredItems = originalFilteredItems;
  });
});
