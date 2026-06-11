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

const elements = new Map();
function getElement(selector) {
  if (!elements.has(selector)) {
    elements.set(selector, createElementStub());
  }
  return elements.get(selector);
}

const calls = [];
const context = {
  console,
  crypto: { randomUUID: () => "test-id" },
  document: {
    querySelector(selector) {
      return getElement(selector);
    },
  },
  localStorage: {
    getItem() {
      return null;
    },
    setItem() {},
    removeItem() {},
  },
  fetch: async (url, options = {}) => {
    calls.push({ url, options });
    return {
      ok: true,
      status: 200,
      async json() {
        return {
          items: [
            {
              id: 1,
              requestType: "next_question",
              retrieverName: "role_knowledge",
              retrievalMode: "keyword",
              hitCount: 3,
              usedInPrompt: true,
              queryText: "AI 应用开发实习生 RAG",
              hits: [
                {
                  title: "RAG 基础流程",
                  score: 12,
                  matchedTokens: ["rag", "召回"],
                  metadata: {
                    knowledgeBase: "role_knowledge",
                    positionTag: "ai_app_intern",
                    interviewStage: "技术追问",
                  },
                },
              ],
              quality: {
                level: "good",
                label: "命中良好",
                hitCount: 3,
                maxScore: 12,
                averageScore: 8,
                databaseHitCount: 1,
                seedHitCount: 2,
                reason: "召回数量和分数都较稳定，可以作为 prompt 上下文使用。",
              },
              createdAt: "2026-06-04T12:00:00",
            },
          ],
        };
      },
    };
  },
  FormData: class FormData {
    append() {}
  },
  URLSearchParams,
  Intl,
  Date,
  Error,
};

const appCode = fs
  .readFileSync("app.js", "utf8")
  .replace(/loadAuthState\(\);[\s\S]*?renderUserCenter\(\);\s*}\);\s*/, "");

const testCode = `
(async () => {
  authState.accessToken = "access-token";
  authState.user = { id: 1, email: "student@example.com", username: "student" };
  ragDebugContent.innerHTML = "<p>existing debug context</p>";
  await loadRagLogs();
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.equal(calls[0].url, "/api/rag/logs/recent?limit=9");
assert.match(getElement("#ragLogContent").innerHTML, /role_knowledge/);
assert.equal(getElement("#ragDebugContent").innerHTML, "");
assert.match(getElement("#ragLogContent").innerHTML, /命中 3 条/);
assert.match(getElement("#ragLogContent").innerHTML, /RAG 基础流程/);
assert.match(getElement("#ragLogContent").innerHTML, /命中良好/);
assert.match(getElement("#ragLogContent").innerHTML, /最高分 12/);
assert.match(getElement("#ragLogContent").innerHTML, /AI 应用开发实习生 RAG/);
assert.match(getElement("#ragLogContent").innerHTML, /已进入 prompt/);
assert.match(getElement("#ragLogContent").innerHTML, /rag、召回/);
assert.match(getElement("#ragLogContent").innerHTML, /knowledgeBase: role_knowledge/);
assert.match(getElement("#ragLogContent").innerHTML, /positionTag: ai_app_intern/);
