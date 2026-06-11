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
    __listeners: new Map(),
    classList: { add() {}, remove() {}, toggle() {} },
    addEventListener(eventName, handler) {
      this.__listeners.set(eventName, handler);
    },
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

function task(overrides = {}) {
  return {
    id: 7,
    weakTag: "rag_quality",
    weakLabel: "RAG 质量评估",
    title: "RAG 质量评估专项训练",
    description: "练习 Hit@K、MRR 和关键词覆盖率。",
    status: "todo",
    priority: "high",
    masteryScore: 45,
    attemptCount: 0,
    metadata: { source: "report" },
    ...overrides,
  };
}

const calls = [];
const context = {
  console,
  calls,
  crypto: { randomUUID: () => "test-id" },
  document: { querySelector: (selector) => getElement(selector) },
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
  fetch: async (url, options = {}) => {
    calls.push({ url, options });
    if (url === "/api/training/tasks") {
      return { ok: true, status: 200, async json() { return { items: [task()] }; } };
    }
    if (url === "/api/training/tasks/7/start") {
      return { ok: true, status: 200, async json() { return task({ status: "in_progress", attemptCount: 1 }); } };
    }
    return { ok: true, status: 200, async json() { return {}; } };
  },
  FormData: class FormData { append() {} },
  URLSearchParams,
  Intl,
  Date,
  Error,
};

const appCode = fs.readFileSync("app.js", "utf8").replace(/loadAuthState\(\);[\s\S]*$/s, "");
const testCode = `
(async () => {
  authState.accessToken = "access-token";
  authState.user = { id: 1, email: "student@example.com", username: "student", role: "user" };

  const refreshHandler = trainingRefreshButton.__listeners.get("click");
  const listHandler = trainingTaskList.__listeners.get("click");
  const detailHandler = trainingTaskDetail.__listeners.get("click");

  if (!refreshHandler || !listHandler || !detailHandler) {
    throw new Error("training center click handlers are not registered");
  }

  await refreshHandler();
  listHandler({
    target: {
      closest(selector) {
        return selector === "[data-training-task-id]" ? { dataset: { trainingTaskId: "7" } } : null;
      },
    },
  });
  await detailHandler({
    target: {
      closest(selector) {
        return selector === "[data-training-start]" ? { dataset: { trainingStart: "7" } } : null;
      },
    },
  });

  globalThis.__result = {
    selectedTaskId: session.training.selectedTaskId,
    html: trainingTaskList.innerHTML + trainingTaskDetail.innerHTML,
  };
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.deepEqual(
  calls.map((call) => [call.url, call.options.method]),
  [
    ["/api/training/tasks", "GET"],
    ["/api/training/tasks/7/start", "POST"],
  ]
);
assert.equal(context.__result.selectedTaskId, 7);
assert.match(context.__result.html, /训练中/);
