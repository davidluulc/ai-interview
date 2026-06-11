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
const calls = [];
function getElement(selector) {
  if (!elements.has(selector)) {
    elements.set(selector, createElementStub());
  }
  return elements.get(selector);
}

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
  fetch: async (url) => {
    calls.push(String(url));
    if (String(url).startsWith("/api/rag/debug")) {
      return jsonResponse(200, {
        roleKnowledge: [
          {
            title: "RAG 文档切片",
            score: 9,
            matchedKeywords: ["RAG"],
            content: "文档切片用于召回。",
            matchedQueryVariant: "stage",
            queryVariants: [{ name: "base" }, { name: "role" }, { name: "stage" }],
            rerankScore: 0.95,
            rankChange: 1,
            rerankExplanation: "rerankScore=0.95, rank 2 -> 1",
          },
        ],
        questionBank: [],
        candidateMemory: [],
        candidateProfile: { hasHistory: false },
        quality: {
          roleKnowledge: {
            level: "good",
            label: "命中良好",
            hitCount: 1,
            maxScore: 9,
            averageScore: 9,
            databaseHitCount: 1,
            seedHitCount: 0,
          },
          questionBank: {
            level: "miss",
            label: "未命中",
            hitCount: 0,
            maxScore: 0,
            averageScore: 0,
            databaseHitCount: 0,
            seedHitCount: 0,
          },
          candidateMemory: {
            level: "miss",
            label: "未命中",
            hitCount: 0,
            maxScore: 0,
            averageScore: 0,
            databaseHitCount: 0,
            seedHitCount: 0,
          },
        },
        explanations: {
          roleKnowledge: {
            retrieverLabel: "岗位知识库",
            hitCount: 1,
            qualityLabel: "命中良好",
            topTitles: ["RAG 质量评估与可观测面板"],
            matchedTerms: ["Hit@K", "MRR", "关键词覆盖率"],
            developerSummary: "岗位知识库命中 1 条，质量为命中良好，主要命中：RAG 质量评估与可观测面板。",
          },
        },
      });
    }
    return jsonResponse(200, { items: [] });
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
const css = fs.readFileSync("styles.css", "utf8");

const testCode = `
(async () => {
  authState.accessToken = "access-token";
  authState.user = { id: 1, email: "student@example.com", username: "student" };
  ragLogContent.innerHTML = "<p>existing logs</p>";
  targetRoleInput.value = "AI 应用开发实习生";
  resumeInput.value = "FastAPI RAG";
  jdInput.value = "RAG 文档切片";
  await loadRagDebug();
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.match(getElement("#ragDebugContent").innerHTML, /岗位知识库/);
assert.match(getElement("#ragDebugContent").innerHTML, /命中良好/);
assert.match(getElement("#ragDebugContent").innerHTML, /最高分 9/);
assert.match(getElement("#ragDebugContent").innerHTML, /未命中/);
assert.match(getElement("#ragDebugContent").innerHTML, /RAG 命中解释/);
assert.match(getElement("#ragDebugContent").innerHTML, /岗位知识库命中 1 条/);
assert.match(getElement("#ragDebugContent").innerHTML, /Hit@K/);
assert.match(getElement("#ragDebugContent").innerHTML, /MRR/);
assert.match(getElement("#ragDebugContent").innerHTML, /多路 query/);
assert.match(getElement("#ragDebugContent").innerHTML, /base \/ role \/ stage/);
assert.match(getElement("#ragDebugContent").innerHTML, /命中 query：stage/);
assert.match(getElement("#ragDebugContent").innerHTML, /重排/);
assert.match(getElement("#ragDebugContent").innerHTML, /rerankScore=0.95/);
assert.doesNotMatch(getElement("#ragDebugContent").innerHTML, /undefined/);
assert.match(css, /\.rag-explanation-card[\s\S]*overflow-wrap:\s*anywhere/s);
assert.equal(calls.some((url) => url.includes("applicationProfileId=")), false);
assert.equal(calls.some((url) => url.startsWith("/api/rag/logs")), false);
assert.equal(getElement("#ragLogContent").innerHTML, "");
