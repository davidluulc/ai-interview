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

  it("uses the unified backend error message when present", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ success: false, error: { code: "HTTP_429", message: "请求过于频繁，请稍后重试。" } }), {
        status: 429,
        headers: { "Content-Type": "application/json" }
      })
    );

    await expect(apiRequest("/api/example")).rejects.toThrow("请求过于频繁，请稍后重试。");
  });

  it("turns gateway timeout html into a friendly model timeout message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("<html><body><h1>504 Gateway Time-out</h1></body></html>", {
        status: 504,
        headers: { "Content-Type": "text/html" }
      })
    );

    await expect(apiRequest("/api/interview/next-question")).rejects.toThrow(
      "模型响应超时，请稍后重试。本轮回答已保留。"
    );
  });

  it("turns gateway html into a friendly service unavailable message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("<html><body><h1>502 Bad Gateway</h1></body></html>", {
        status: 502,
        headers: { "Content-Type": "text/html" }
      })
    );

    await expect(apiRequest("/api/auth/login")).rejects.toThrow("服务暂时不可用，请稍后重试。");
  });

  it("clears saved tokens", () => {
    setApiTokens({ accessToken: "access-1", refreshToken: "refresh-1" });
    clearApiTokens();

    expect(localStorage.getItem("ai_interview_access_token")).toBeNull();
    expect(localStorage.getItem("ai_interview_refresh_token")).toBeNull();
  });
});
