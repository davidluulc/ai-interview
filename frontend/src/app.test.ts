import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.vue";

const authStore = {
  restore: vi.fn()
};

vi.mock("@/stores/auth", () => ({
  useAuthStore: () => authStore
}));

describe("app bootstrap", () => {
  beforeEach(() => {
    authStore.restore.mockReset();
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
});
