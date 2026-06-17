import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AppLayout from "./AppLayout.vue";

const replaceMock = vi.fn();
const authStore = {
  user: { id: 1, email: "admin@ai-interview.com", username: "admin", role: "admin" },
  isAdmin: true,
  logout: vi.fn()
};

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    useRouter: () => ({ replace: replaceMock })
  };
});

vi.mock("@/stores/auth", () => ({
  useAuthStore: () => authStore
}));

const globalConfig = {
  stubs: {
    RouterLink: {
      props: ["to"],
      template: "<a><slot /></a>"
    }
  }
};

describe("app layout", () => {
  beforeEach(() => {
    replaceMock.mockReset();
    authStore.isAdmin = true;
    authStore.logout.mockReset();
  });

  it("lets users log out and returns them to the login page", async () => {
    authStore.logout.mockResolvedValue(undefined);
    const wrapper = mount(AppLayout, { global: globalConfig });

    await wrapper.get("button.logout-button").trigger("click");

    expect(authStore.logout).toHaveBeenCalled();
    expect(replaceMock).toHaveBeenCalledWith("/vue/auth/login");
  });

  it("shows the admin navigation item for admin users", () => {
    authStore.isAdmin = true;
    const wrapper = mount(AppLayout, { global: globalConfig });

    expect(wrapper.text()).toContain("后台");
  });

  it("hides the admin navigation item for normal users", () => {
    authStore.isAdmin = false;
    const wrapper = mount(AppLayout, { global: globalConfig });

    expect(wrapper.text()).not.toContain("后台");
  });
});
