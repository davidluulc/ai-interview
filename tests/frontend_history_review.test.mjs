import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

function createElementStub() {
  const classes = new Set(["hidden"]);
  return {
    value: "",
    textContent: "",
    innerHTML: "",
    disabled: false,
    dataset: {},
    files: [],
    listeners: {},
    classList: {
      add(name) {
        classes.add(name);
      },
      remove(name) {
        classes.delete(name);
      },
      toggle(name, force) {
        if (force === undefined ? !classes.has(name) : force) {
          classes.add(name);
        } else {
          classes.delete(name);
        }
      },
      contains(name) {
        return classes.has(name);
      },
    },
    addEventListener(type, handler) {
      this.listeners[type] = handler;
    },
    querySelectorAll() {
      return [];
    },
    closest() {
      return null;
    },
    scrollIntoView() {},
    focus() {},
  };
}

const elements = new Map();
function getElement(selector) {
  if (!elements.has(selector)) {
    elements.set(selector, createElementStub());
  }
  return elements.get(selector);
}

const storage = new Map();
const context = {
  console,
  crypto: { randomUUID: () => "test-id" },
  document: { querySelector: (selector) => getElement(selector) },
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
  fetch: async () => ({ ok: true, status: 200, async json() { return {}; } }),
  FormData: class FormData {
    append() {}
  },
  URLSearchParams,
  Intl,
  Date,
  Error,
};

const appCode = fs.readFileSync("app.js", "utf8").replace(/loadAuthState\(\);[\s\S]*$/s, "");
const testCode = `
(async () => {
  localStorage.setItem(historyStorageKey, JSON.stringify([
    {
      id: 143,
      createdAt: "2026-06-05T06:58:00",
      profile: { candidateName: "David", targetRole: "AI App Intern" },
      answers: [{ stage: "Tech", focus: "RAG 召回链路", question: "How does RAG work?", answer: "Retrieve then generate." }],
      report: {
        score: 52,
        strengths: ["clear"],
        risks: ["risk-a"],
        actions: ["practice-a"],
        questionReviews: [
          {
            index: 1,
            focus: "RAG 召回链路",
            question: "How does RAG work?",
            answerStatus: "模糊",
            whyAsked: "用于确认检索增强生成的基本链路。",
            missingPoints: ["召回", "生成"],
            referenceDirection: "先讲 retrieve，再讲 generate。",
            trainingAction: "画出 RAG 请求链路图。"
          }
        ],
        trainingPlan: {
          weakTopics: [
            {
              focus: "RAG 召回链路",
              reason: "回答缺少召回和生成之间的边界。",
              trainingAction: "画出 RAG 请求链路图。"
            }
          ],
          nextRoundPriority: ["RAG 召回链路"],
          practiceQuestions: ["请说明 RAG 的 retrieve 和 generate 分别解决什么问题。"],
          oneMinuteTemplates: ["背景：需要回答 RAG 链路；做法：先 retrieve，再 generate；结果：降低幻觉。"],
          shouldRetry: true
        }
      }
    }
  ]));

  await renderHistory();
  const clickHandler = historyList.listeners.click;
  clickHandler({
    target: {
      closest(selector) {
        return selector === "[data-review-id]" ? { dataset: { reviewId: "143" } } : null;
      }
    }
  });

  globalThis.__result = {
    reviewHidden: reviewPanel.classList.contains("hidden"),
    reviewHtml: reviewPanel.innerHTML,
  };
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.equal(context.__result.reviewHidden, false);
assert.match(context.__result.reviewHtml, /AI App Intern/);
assert.match(context.__result.reviewHtml, /risk-a/);
assert.match(context.__result.reviewHtml, /RAG 召回链路/);
assert.match(context.__result.reviewHtml, /逐题学习复盘/);
assert.match(context.__result.reviewHtml, /用于确认检索增强生成的基本链路/);
assert.match(context.__result.reviewHtml, /画出 RAG 请求链路图/);
assert.match(context.__result.reviewHtml, /下一轮训练计划/);
assert.match(context.__result.reviewHtml, /请说明 RAG 的 retrieve 和 generate/);
assert.match(context.__result.reviewHtml, /建议重练/);
assert.doesNotMatch(context.__result.reviewHtml, /1\\. Tech/);
