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
    const payloads = {
      "/api/admin/summary": {
        userCount: 2,
        interviewRecordCount: 3,
        ragDocumentCount: 4,
        ragRetrievalLogCount: 5,
        agentDecisionLogCount: 6,
      },
      "/api/admin/users": { items: [{ id: 1, email: "admin@example.com", username: "admin", role: "admin" }] },
      "/api/admin/rag/documents": { items: [{ id: 11, title: "岗位知识", knowledgeBase: "role_knowledge" }] },
      "/api/admin/rag/logs": { items: [{ id: 9, retrieverName: "role_knowledge", queryText: "RAG", hitCount: 2 }] },
      "/api/admin/rag/quality": {
        summary: {
          lowQualityCount: 2,
          emptyRecallCount: 1,
          weakRecallCount: 1,
          unusedInPromptCount: 0,
        },
        items: [
          {
            id: 101,
            queryText: "empty recall query",
            retrieverName: "role_knowledge",
            issueType: "empty_recall",
            quality: { level: "miss", label: "未命中" },
            recommendation: "补充知识库或优化 query rewrite",
          },
        ],
      },
      "/api/admin/agent/logs": { items: [{ id: 10, nextAction: "deepen", focus: "Agent State", reason: "回答完整" }] },
    };
    return { ok: true, status: 200, async json() { return payloads[url] || {}; } };
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
  authState.user = { id: 2, email: "admin@example.com", username: "admin", role: "admin" };
  await loadAdminDashboard();
  globalThis.__result = {
    html: adminDashboardContent.innerHTML,
    calls: globalThis.calls.map((call) => [call.url, call.options.method]),
  };
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.equal(
  JSON.stringify(context.__result.calls.slice(0, 6)),
  JSON.stringify([
    ["/api/admin/summary", "GET"],
    ["/api/admin/users", "GET"],
    ["/api/admin/rag/documents", "GET"],
    ["/api/admin/rag/logs", "GET"],
    ["/api/admin/rag/quality", "GET"],
    ["/api/admin/agent/logs", "GET"],
  ])
);
assert.match(context.__result.html, /用户总数/);
assert.match(context.__result.html, /admin@example.com/);
assert.match(context.__result.html, /岗位知识/);
assert.match(context.__result.html, /role_knowledge/);
assert.match(context.__result.html, /低质量召回/);
assert.match(context.__result.html, /质量问题分布/);
assert.match(context.__result.html, /空召回/);
assert.match(context.__result.html, /弱召回/);
assert.match(context.__result.html, /未进入 Prompt/);
assert.match(context.__result.html, /建议动作/);
assert.match(context.__result.html, /empty recall query/);
assert.match(context.__result.html, /deepen/);
assert.doesNotMatch(context.__result.html, /undefined/);
