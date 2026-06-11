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
              nextAction: "lower_difficulty",
              stage: "技术追问",
              difficulty: "basic",
              focus: "RAG 日志字段",
              reason: "候选人回答不知道，需要先降低难度。",
              tools: ["retrieve_context", "generate_question"],
              fallbackUsed: false,
              debugSignals: {
                weakAnswerStreak: 2,
                repeatedQuestionCount: 1,
                topicLocked: false,
                guardrailApplied: true,
                topicShifted: true,
                triggerRules: ["weak_answer_streak", "topic_shift"],
              },
              guardrailApplied: true,
              topicShift: { from: "rag_log_json", to: "rag_basic" },
              decision: {
                triggerRules: ["weak_answer"],
                agentMode: "coach",
                nodeTrace: [
                  {
                    nodeName: "observe_state",
                    inputSummary: { historyCount: 2 },
                    outputSummary: { answerStatus: "不会" },
                    fallbackUsed: false,
                  },
                  {
                    nodeName: "analyze_answer",
                    inputSummary: { historyCount: 2, lastAnswerLength: 3 },
                    outputSummary: { answerStatus: "不会", weakAnswerStreak: 2 },
                    fallbackUsed: false,
                  },
                  {
                    nodeName: "retrieve_context",
                    inputSummary: { nextStage: "技术追问" },
                    outputSummary: { roleHitCount: 1, questionHitCount: 2, memoryHitCount: 0 },
                    fallbackUsed: false,
                  },
                  {
                    nodeName: "select_action",
                    inputSummary: { remainingRounds: 6 },
                    outputSummary: { nextAction: "lower_difficulty" },
                    fallbackUsed: false,
                  },
                ],
                toolCalls: [
                  {
                    toolName: "retrieve_role_knowledge",
                    inputSummary: { query: "AI 应用开发实习生 RAG", limit: 3 },
                    outputSummary: { hitCount: 1, topScores: [0.91] },
                    success: true,
                    elapsedMs: 12,
                  },
                  {
                    toolName: "retrieve_question_bank",
                    inputSummary: { query: "AI 应用开发实习生 技术追问", limit: 3 },
                    outputSummary: { hitCount: 2, topScores: [0.88, 0.75] },
                    success: true,
                    elapsedMs: 15,
                  },
                ],
              },
              state: { roundCount: 2, answerStatus: "不会" },
              createdAt: "2026-06-06T12:00:00",
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
  agentLogContent.innerHTML = "<p>existing agent logs</p>";
  await loadAgentLogs();
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.equal(calls[0].url, "/api/agent/logs/recent?limit=8");
assert.match(getElement("#agentLogContent").innerHTML, /lower_difficulty/);
assert.match(getElement("#agentLogContent").innerHTML, /RAG 日志字段/);
assert.match(getElement("#agentLogContent").innerHTML, /候选人回答不知道/);
assert.match(getElement("#agentLogContent").innerHTML, /retrieve_context/);
assert.match(getElement("#agentLogContent").innerHTML, /weak_answer/);
assert.match(getElement("#agentLogContent").innerHTML, /模型决策/);
assert.match(getElement("#agentLogContent").innerHTML, /节点链路/);
assert.match(getElement("#agentLogContent").innerHTML, /observe_state/);
assert.match(getElement("#agentLogContent").innerHTML, /analyze_answer/);
assert.match(getElement("#agentLogContent").innerHTML, /select_action/);
assert.match(getElement("#agentLogContent").innerHTML, /工具调用/);
assert.match(getElement("#agentLogContent").innerHTML, /retrieve_role_knowledge/);
assert.match(getElement("#agentLogContent").innerHTML, /命中 1 条/);
assert.match(getElement("#agentLogContent").innerHTML, /耗时 12ms/);
assert.match(getElement("#agentLogContent").innerHTML, /调试摘要/);
assert.match(getElement("#agentLogContent").innerHTML, /已介入/);
assert.match(getElement("#agentLogContent").innerHTML, /连续弱回答/);
assert.match(getElement("#agentLogContent").innerHTML, /rag_log_json/);
assert.match(getElement("#agentLogContent").innerHTML, /topic_shift/);
assert.doesNotMatch(getElement("#agentLogContent").innerHTML, /undefined/);
