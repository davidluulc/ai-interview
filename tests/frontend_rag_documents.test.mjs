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
    reset() {},
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
    if (url === "/api/rag/documents" && options.method === "POST") {
      return jsonResponse(200, {
        id: 2,
        title: "RAG 日志题库",
        knowledgeBase: "question_bank",
        sourceType: "manual",
        content: "请说明 RAG 命中日志如何帮助调试召回质量。",
        metadata: { positionTag: "ai_app_intern" },
        chunkCount: 1,
      });
    }
    if (url === "/api/rag/documents/2") {
      return jsonResponse(200, {
        document: {
          id: 2,
          title: "RAG 日志题库",
          knowledgeBase: "question_bank",
          status: "enabled",
          visibility: "public",
          chunkCount: 1,
          duplicateChunkCount: 0,
          metadata: { positionTag: "ai_app_intern", category: "technical" },
        },
        chunks: [
          {
            id: 9,
            content: "请说明 RAG 命中日志如何帮助调试召回质量。",
            keywords: ["RAG", "命中日志"],
          },
        ],
      });
    }
    return jsonResponse(200, {
      items: [
        {
          id: 1,
          title: "FastAPI 岗位知识",
          knowledgeBase: "role_knowledge",
          status: "enabled",
          visibility: "private",
          chunkCount: 2,
          duplicateChunkCount: 1,
          metadata: { positionTag: "python_backend_intern", category: "technical" },
          createdAt: "2026-06-04T12:00:00",
        },
      ],
    });
  },
  FormData: class FormData {
    append() {}
  },
  URLSearchParams,
  Intl,
  Date,
  Error,
};

function jsonResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return payload;
    },
  };
}

const appCode = fs
  .readFileSync("app.js", "utf8")
  .replace(/loadAuthState\(\);[\s\S]*$/s, "");

const testCode = `
(async () => {
  authState.accessToken = "access-token";
  authState.user = { id: 1, email: "student@example.com", username: "student" };
  await loadRagDocuments();
  ragDocumentTitleInput.value = "RAG 日志题库";
  ragKnowledgeBaseInput.value = "question_bank";
  ragDocumentContentInput.value = "请说明 RAG 命中日志如何帮助调试召回质量。";
  await submitRagDocument({ preventDefault() {} });
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

const ragDocumentCalls = calls.filter((call) => String(call.url).startsWith("/api/rag/documents"));

assert.equal(ragDocumentCalls[0].url, "/api/rag/documents");
assert.equal(ragDocumentCalls[1].url, "/api/rag/documents");
assert.equal(ragDocumentCalls[1].options.method, "POST");
assert.equal(JSON.parse(ragDocumentCalls[1].options.body).knowledgeBase, "question_bank");
assert.match(getElement("#ragDocumentList").innerHTML, /FastAPI 岗位知识/);
assert.match(getElement("#ragDocumentList").innerHTML, /启用/);
assert.match(getElement("#ragDocumentList").innerHTML, /私有/);
assert.match(getElement("#ragDocumentList").innerHTML, /重复 chunk 1/);
assert.match(getElement("#ragDocumentList").innerHTML, /positionTag/);
assert.match(getElement("#ragDocumentList").innerHTML, /python_backend_intern/);
assert.match(getElement("#ragDocumentDetail").innerHTML, /RAG 命中日志/);
assert.match(getElement("#ragDocumentDetail").innerHTML, /公开/);
assert.match(getElement("#ragDocumentDetail").innerHTML, /chunk 1/);
assert.match(getElement("#ragDocumentDetail").innerHTML, /重复 chunk 0/);
assert.match(getElement("#ragDocumentDetail").innerHTML, /ai_app_intern/);
assert.doesNotMatch(getElement("#ragDocumentList").innerHTML, /undefined/);
assert.doesNotMatch(getElement("#ragDocumentDetail").innerHTML, /undefined/);
