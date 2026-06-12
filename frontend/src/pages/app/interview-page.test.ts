import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import InterviewPage from "./InterviewPage.vue";

const interviewStore = {
  messages: [{ role: "interviewer", content: "请先做一个一分钟自我介绍。" }],
  draft: "",
  loading: false,
  error: "",
  decisionSummary: "当前处于学习辅导模式，会先确认基础概念。",
  submitAnswer: vi.fn()
};

const profilesStore = {
  currentProfileId: 3,
  currentProfile: {
    id: 3,
    title: "后端实习投递",
    targetRole: "Python 后端开发实习生"
  }
};

vi.mock("@/stores/interview", () => ({
  useInterviewStore: () => interviewStore
}));

vi.mock("@/stores/profiles", () => ({
  useProfilesStore: () => profilesStore
}));

describe("interview page", () => {
  beforeEach(() => {
    interviewStore.submitAnswer.mockReset();
  });

  it("renders chat and decision context panels", () => {
    const wrapper = mount(InterviewPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("面试训练台");
    expect(wrapper.text()).toContain("请先做一个一分钟自我介绍。");
    expect(wrapper.text()).toContain("为什么这样问");
    expect(wrapper.text()).toContain("当前处于学习辅导模式");
  });
});
