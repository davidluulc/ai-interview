import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const css = readFileSync(
  path.join(path.dirname(fileURLToPath(import.meta.url)), "tokens.css"),
  "utf8"
);

describe("brut tokens", () => {
  it.each(["--paper", "--ink", "--action", "--ok", "--warn", "--danger", "--score-5", "--heat-3", "--shadow-3", "--hazard", "--font-mono", "--text-page", "--s4", "--ease-out"])("defines %s", (token) => {
    expect(css).toContain(`${token}:`);
  });
});
