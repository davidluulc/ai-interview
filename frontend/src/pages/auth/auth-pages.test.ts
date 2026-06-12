import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "./LoginPage.vue";
import RegisterPage from "./RegisterPage.vue";

const pushMock = vi.fn();
const authStore = {
  login: vi.fn(),
  register: vi.fn(),
  loading: false,
  error: ""
};

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    useRouter: () => ({ push: pushMock })
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

describe("auth pages", () => {
  beforeEach(() => {
    pushMock.mockReset();
    authStore.login.mockReset();
    authStore.register.mockReset();
    authStore.loading = false;
    authStore.error = "";
  });

  it("submits login credentials and navigates to the interview workspace", async () => {
    authStore.login.mockResolvedValue(undefined);
    const wrapper = mount(LoginPage, { global: globalConfig });

    await wrapper.find('input[type="email"]').setValue("student@example.com");
    await wrapper.find('input[type="password"]').setValue("password123");
    await wrapper.find("form").trigger("submit");

    expect(authStore.login).toHaveBeenCalledWith("student@example.com", "password123");
    expect(pushMock).toHaveBeenCalledWith("/vue/app/interview");
  });

  it("submits registration data and navigates to the interview workspace", async () => {
    authStore.register.mockResolvedValue(undefined);
    const wrapper = mount(RegisterPage, { global: globalConfig });

    await wrapper.find('input[type="email"]').setValue("student@example.com");
    await wrapper.find('input[name="username"]').setValue("student");
    await wrapper.find('input[type="password"]').setValue("password123");
    await wrapper.find("form").trigger("submit");

    expect(authStore.register).toHaveBeenCalledWith("student@example.com", "student", "password123");
    expect(pushMock).toHaveBeenCalledWith("/vue/app/interview");
  });
});
