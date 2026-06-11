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
    classList: { add() {}, remove() {}, toggle() {} },
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
    if (url === "/api/training/tasks/7/complete") {
      return { ok: true, status: 200, async json() { return task({ status: "done", masteryScore: 60, attemptCount: 1 }); } };
    }
    if (url === "/api/training/tasks/7/archive") {
      return { ok: true, status: 200, async json() { return task({ status: "archived", masteryScore: 60, attemptCount: 1 }); } };
    }
    throw new Error(`Unexpected fetch URL: ${url}`);
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
  await loadTrainingTasks();
  await startTrainingTask(7);
  await completeTrainingTask(7);
  await archiveTrainingTask(7);
  globalThis.__result = {
    html: trainingTaskList.innerHTML + trainingTaskDetail.innerHTML,
    task: session.training.tasks[0],
    calls: globalThis.calls,
  };
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.deepEqual(
  calls.map((call) => [call.url, call.options.method]),
  [
    ["/api/training/tasks", "GET"],
    ["/api/training/tasks/7/start", "POST"],
    ["/api/training/tasks/7/complete", "POST"],
    ["/api/training/tasks/7/archive", "POST"],
  ]
);
assert.match(calls[2].options.body, /完整/);
assert.equal(context.__result.task.status, "archived");
assert.equal(context.__result.task.masteryScore, 60);
assert.match(context.__result.html, /已归档/);
assert.doesNotMatch(context.__result.html, /undefined/);
