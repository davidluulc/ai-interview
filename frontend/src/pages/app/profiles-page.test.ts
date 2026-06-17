import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProfilesPage from "./ProfilesPage.vue";

const push = vi.fn();

const profileFixtures = [
  {
    id: 1,
    title: "后端实习投递",
    targetRole: "Python 后端开发实习生",
    company: "Example AI",
    jd: "负责 FastAPI 接口开发",
    resume: "有 AI 模拟面试系统项目经历"
  },
  {
    id: 2,
    title: "AI 应用开发投递",
    targetRole: "AI 应用开发实习生",
    company: "Future AI",
    jd: "熟悉 RAG 和 Agent",
    resume: "熟悉 Python 后端"
  }
];

const profilesStore = {
  profiles: [...profileFixtures],
  currentProfileId: 1 as number | null,
  currentProfile: profileFixtures[0] as (typeof profileFixtures)[number] | null,
  loading: false,
  error: "",
  loadProfiles: vi.fn(),
  createProfile: vi.fn(),
  selectProfile: vi.fn()
};

vi.mock("vue-router", () => ({
  useRouter: () => ({ push })
}));

vi.mock("@/stores/profiles", () => ({
  useProfilesStore: () => profilesStore
}));

describe("profiles page", () => {
  beforeEach(() => {
    push.mockReset();
    profilesStore.loadProfiles.mockReset();
    profilesStore.selectProfile.mockReset();
    profilesStore.createProfile.mockReset();
    profilesStore.profiles = [...profileFixtures];
    profilesStore.currentProfileId = 1;
    profilesStore.currentProfile = profileFixtures[0];
  });

  it("loads and displays the current application profile", () => {
    const wrapper = mount(ProfilesPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(profilesStore.loadProfiles).toHaveBeenCalled();
    expect(wrapper.text()).toContain("当前档案");
    expect(wrapper.text()).toContain("后端实习投递");
    expect(wrapper.text()).toContain("Python 后端开发实习生");
    expect(wrapper.text()).toContain("Example AI");
  });

  it("selects a profile before navigating to the interview page", async () => {
    const wrapper = mount(ProfilesPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    await wrapper.get('[data-testid="start-profile-2"]').trigger("click");

    expect(profilesStore.selectProfile).toHaveBeenCalledWith(2);
    expect(push).toHaveBeenCalledWith("/vue/app/interview");
  });

  it("shows a clear empty state when there are no profiles", () => {
    profilesStore.profiles = [];
    profilesStore.currentProfile = null;
    profilesStore.currentProfileId = null;

    const wrapper = mount(ProfilesPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(wrapper.text()).toContain("还没有投递档案");
    expect(wrapper.text()).toContain("先创建一个档案");
  });
});
