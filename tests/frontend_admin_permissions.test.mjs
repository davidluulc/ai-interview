import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function createElementStub() {
  return {
    value: "",
    textContent: "",
    innerHTML: "",
    disabled: false,
    dataset: {},
    files: [],
    classList: {
      added: [],
      removed: [],
      add(value) { this.added.push(value); },
      remove(value) { this.removed.push(value); },
      toggle() {},
    },
    addEventListener() {},
    querySelectorAll() { return []; },
    closest() { return null; },
    scrollIntoView() {},
    focus() {},
  };
}

const elements = new Map();
function getElement(selector) {
  if (!elements.has(selector)) elements.set(selector, createElementStub());
  return elements.get(selector);
}

const context = {
  console,
  crypto: { randomUUID: () => "test-id" },
  document: { querySelector: (selector) => getElement(selector) },
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
  fetch: async () => ({ ok: true, status: 200, async json() { return {}; } }),
  FormData: class FormData { append() {} },
  URLSearchParams,
  Intl,
  Date,
  Error,
};

const appCode = fs.readFileSync("app.js", "utf8").replace(/loadAuthState\(\);[\s\S]*$/s, "");
const testCode = `
authState.user = { id: 1, email: "u@example.com", username: "user", role: "user" };
renderAdminVisibility();
const userAdded = adminNavButton.classList.added.join(",");

authState.user = { id: 2, email: "a@example.com", username: "admin", role: "admin" };
renderAdminVisibility();
globalThis.__result = {
  userAdded,
  adminRemoved: adminNavButton.classList.removed.join(","),
};
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.match(context.__result.userAdded, /hidden/);
assert.match(context.__result.adminRemoved, /hidden/);
