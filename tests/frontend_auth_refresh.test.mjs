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
      add() {},
      remove() {},
      toggle() {},
    },
    addEventListener() {},
    querySelectorAll() {
      return [];
    },
    closest() {
      return null;
    },
  };
}

function createContext(fetchImpl) {
  const storage = new Map();
  const element = createElementStub();

  return {
    console,
    crypto: { randomUUID: () => "test-id" },
    document: {
      querySelector() {
        return element;
      },
    },
    localStorage: {
      getItem(key) {
        return storage.get(key) ?? null;
      },
      setItem(key, value) {
        storage.set(key, String(value));
      },
      removeItem(key) {
        storage.delete(key);
      },
    },
    fetch: fetchImpl,
    FormData: class FormData {
      append() {}
    },
    URLSearchParams,
    Intl,
    Date,
    Error,
  };
}

function jsonResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return payload;
    },
  };
}

const calls = [];
const context = createContext(async (url, options = {}) => {
  calls.push({ url, options });

  if (url === "/api/history" && calls.filter((call) => call.url === "/api/history").length === 1) {
    return jsonResponse(401, { detail: "Token expired" });
  }

  if (url === "/api/auth/refresh") {
    return jsonResponse(200, {
      accessToken: "new-access-token",
      tokenType: "bearer",
      user: { id: 1, email: "student@example.com", username: "student" },
    });
  }

  return jsonResponse(200, [{ id: "history-1" }]);
});

const appCode = fs
  .readFileSync("app.js", "utf8")
  .replace(/setupForm\.addEventListener[\s\S]*?agentLogButton\.addEventListener\("click", loadAgentLogs\);\s*/, "")
  .replace(/loadAuthState\(\);[\s\S]*$/s, "");
const testCode = `
(async () => {
  authState.accessToken = "expired-access-token";
  authState.refreshToken = "refresh-token";
  authState.user = { id: 1, email: "student@example.com", username: "student" };
  await authFetch("/api/history");
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

const historyCalls = calls.filter((call) => call.url === "/api/history");
const refreshCalls = calls.filter((call) => call.url === "/api/auth/refresh");

assert.equal(historyCalls.length, 2);
assert.equal(refreshCalls.length, 1);
assert.equal(historyCalls[0].options.headers.Authorization, "Bearer expired-access-token");
assert.equal(historyCalls[1].options.headers.Authorization, "Bearer new-access-token");
