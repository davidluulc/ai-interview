import { describe, expect, it } from "vitest";
import { requiresAuth, routes } from "./index";

describe("vue router config", () => {
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
  });
});
