import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiRequest, clearApiTokens, setApiTokens } from "./client";

describe("api client", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("injects the access token into requests", async () => {
    setApiTokens({ accessToken: "access-1", refreshToken: "refresh-1" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      })
    );

    await apiRequest("/api/example");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/example",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer access-1"
        })
      })
    );
  });

  it("throws a readable error when the response is not ok", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "登录已过期" }), {
        status: 401,
        headers: { "Content-Type": "application/json" }
      })
    );

    await expect(apiRequest("/api/example")).rejects.toThrow("登录已过期");
  });

  it("clears saved tokens", () => {
    setApiTokens({ accessToken: "access-1", refreshToken: "refresh-1" });
    clearApiTokens();

    expect(localStorage.getItem("ai_interview_access_token")).toBeNull();
    expect(localStorage.getItem("ai_interview_refresh_token")).toBeNull();
  });
});
