import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProfilesPage from "./ProfilesPage.vue";

const profilesStore = {
  profiles: [
    {
      id: 1,
      title: "后端实习投递",
      targetRole: "Python 后端开发实习生",
      company: "Example AI"
    }
  ],
  currentProfileId: 1,
  loading: false,
  error: "",
  loadProfiles: vi.fn(),
  selectProfile: vi.fn()
};

vi.mock("@/stores/profiles", () => ({
  useProfilesStore: () => profilesStore
}));

describe("profiles page", () => {
  beforeEach(() => {
    profilesStore.loadProfiles.mockReset();
    profilesStore.selectProfile.mockReset();
  });

  it("loads and displays application profiles", () => {
    const wrapper = mount(ProfilesPage, {
      global: {
        stubs: {
          AppLayout: { template: "<main><slot /></main>" }
        }
      }
    });

    expect(profilesStore.loadProfiles).toHaveBeenCalled();
    expect(wrapper.text()).toContain("后端实习投递");
    expect(wrapper.text()).toContain("Python 后端开发实习生");
  });
});
