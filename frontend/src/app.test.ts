import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.vue";

const authStore = {
  restore: vi.fn()
};
const replaceMock = vi.fn();

vi.mock("@/stores/auth", () => ({
  useAuthStore: () => authStore
}));

vi.mock("vue-router", () => ({
  useRouter: () => ({ replace: replaceMock })
}));

describe("app bootstrap", () => {
  beforeEach(() => {
    authStore.restore.mockReset();
    replaceMock.mockReset();
  });

  it("restores the current user when the app starts", () => {
    mount(App, {
      global: {
        stubs: {
          RouterView: { template: "<section />" }
        }
      }
    });

    expect(authStore.restore).toHaveBeenCalled();
  });

  it("redirects to login when the current session is revoked", async () => {
    mount(App, {
      global: {
        stubs: {
          RouterView: { template: "<section />" }
        }
      }
    });

    window.dispatchEvent(new CustomEvent("ai-interview-auth-revoked"));

    expect(replaceMock).toHaveBeenCalledWith("/vue/auth/login");
  });
});
