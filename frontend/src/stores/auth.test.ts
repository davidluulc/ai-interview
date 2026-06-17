import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as authApi from "@/api/auth";
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from "@/api/client";
import { useAuthStore } from "./auth";

vi.mock("@/api/auth", () => ({
  login: vi.fn(),
  register: vi.fn(),
  fetchCurrentUser: vi.fn(),
  logout: vi.fn()
}));

describe("auth store", () => {
  beforeEach(() => {
    localStorage.clear();
    setActivePinia(createPinia());
    vi.mocked(authApi.login).mockReset();
    vi.mocked(authApi.register).mockReset();
    vi.mocked(authApi.fetchCurrentUser).mockReset();
    vi.mocked(authApi.logout).mockReset();
  });

  it("stores tokens and current user after login", async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "access-1",
      refresh_token: "refresh-1"
    });
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValue({
      id: 1,
      email: "student@example.com",
      username: "student"
    });

    const store = useAuthStore();
    await store.login("student@example.com", "password");

    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBe("access-1");
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe("refresh-1");
    expect(store.user?.email).toBe("student@example.com");
  });

  it("exposes whether the current user is an admin", async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: "access-1",
      refresh_token: "refresh-1",
      user: {
        id: 1,
        email: "admin@ai-interview.com",
        username: "admin",
        role: "admin"
      }
    });

    const store = useAuthStore();
    await store.login("admin@ai-interview.com", "password123");

    expect(store.isAdmin).toBe(true);
  });

  it("restores current user when an access token exists", async () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, "access-1");
    vi.mocked(authApi.fetchCurrentUser).mockResolvedValue({
      id: 2,
      email: "restored@example.com",
      username: "restored"
    });

    const store = useAuthStore();
    await store.restore();

    expect(store.user?.username).toBe("restored");
  });

  it("clears tokens and user on logout", async () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, "access-1");
    localStorage.setItem(REFRESH_TOKEN_KEY, "refresh-1");
    vi.mocked(authApi.logout).mockResolvedValue();

    const store = useAuthStore();
    await store.logout();

    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
    expect(store.user).toBeNull();
  });
});
