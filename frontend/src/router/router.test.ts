import { beforeEach, describe, expect, it } from "vitest";
import router, { requiresAuth, routes } from "./index";

describe("vue router config", () => {
  beforeEach(async () => {
    localStorage.clear();
    if (router.currentRoute.value.path !== "/") {
      await router.replace("/");
    }
  });

  it("keeps auth pages public and app pages protected", () => {
    expect(requiresAuth("/vue/auth/login")).toBe(false);
    expect(requiresAuth("/vue/auth/register")).toBe(false);
    expect(requiresAuth("/vue/app/interview")).toBe(true);
  });

  it("defines the main V1 pages", () => {
    const paths = routes.map((route) => route.path);
    expect(paths).toContain("/vue/auth/login");
    expect(paths).toContain("/vue/auth/register");
    expect(paths).toContain("/vue/app/interview");
    expect(paths).toContain("/vue/app/profiles");
    expect(paths).toContain("/vue/app/history");
    expect(paths).toContain("/vue/app/reports/:recordId");
    expect(requiresAuth("/vue/app/reports/:recordId")).toBe(true);
  });

  it("redirects authenticated users away from login pages", async () => {
    localStorage.setItem("ai_interview_access_token", "access-token");

    await router.push("/vue/auth/login");
    await router.isReady();

    expect(router.currentRoute.value.path).toBe("/vue/app/interview");
  });

  it("redirects authenticated users away from register pages", async () => {
    localStorage.setItem("ai_interview_access_token", "access-token");

    await router.push("/vue/auth/register");
    await router.isReady();

    expect(router.currentRoute.value.path).toBe("/vue/app/interview");
  });
});
