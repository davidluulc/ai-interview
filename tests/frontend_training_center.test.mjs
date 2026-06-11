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
      return {
        ok: true,
        status: 200,
        async json() {
          return {
            items: [
              {
                id: 7,
                weakTag: "rag_quality",
                weakLabel: "RAG 质量评估",
                title: "RAG 质量评估专项训练",
                description: "练习 Hit@K、MRR 和关键词覆盖率。",
                status: "todo",
                priority: "high",
                masteryScore: 45,
                attemptCount: 0,
                recommendedQuestion: "Hit@K、MRR 和关键词覆盖率分别解决什么问题？",
                metadata: { source: "report" },
              },
            ],
          };
        },
      };
    }
    return {
      ok: true,
      status: 200,
      async json() {
        return { id: 7, status: "in_progress", masteryScore: 45 };
      },
    };
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
  renderTrainingCenter();
  globalThis.__result = {
    html: trainingTaskList.innerHTML + trainingTaskDetail.innerHTML,
    calls: globalThis.calls,
  };
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.equal(calls[0].url, "/api/training/tasks");
assert.match(context.__result.html, /RAG 质量评估专项训练/);
assert.match(context.__result.html, /45/);
assert.match(context.__result.html, /高优先级/);
assert.match(context.__result.html, /下一步训练/);
assert.match(context.__result.html, /掌握度/);
assert.match(context.__result.html, /Hit@K/);
assert.match(context.__result.html, /分别解决什么问题/);
assert.match(context.__result.html, /开始训练/);
assert.doesNotMatch(context.__result.html, /undefined/);
