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

function createProductSectionStub(sectionName) {
  const element = createElementStub();
  element.dataset.productSection = sectionName;
  return element;
}

function createProductNavButtonStub(sectionName) {
  const element = createElementStub();
  element.dataset.sectionTarget = sectionName;
  element.setAttribute = () => {};
  return element;
}

const elements = new Map();
function getElement(selector) {
  if (!elements.has(selector)) elements.set(selector, createElementStub());
  return elements.get(selector);
}

const calls = [];
let responseCount = 0;
const productSectionStubs = [
  createProductSectionStub("account-profile"),
  createProductSectionStub("interview-workbench"),
  createProductSectionStub("training-center"),
  createProductSectionStub("rag-knowledge"),
  createProductSectionStub("admin-dashboard"),
];
const productNavButtonStubs = [
  createProductNavButtonStub("account-profile"),
  createProductNavButtonStub("interview-workbench"),
  createProductNavButtonStub("training-center"),
  createProductNavButtonStub("rag-knowledge"),
  createProductNavButtonStub("admin-dashboard"),
];
const context = {
  console,
  calls,
  crypto: { randomUUID: () => "test-id" },
  document: {
    querySelector: (selector) => getElement(selector),
    querySelectorAll: (selector) => {
      if (selector === "[data-product-section]") return productSectionStubs;
      if (selector === "[data-section-target]") return productNavButtonStubs;
      return [];
    },
  },
  localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
  fetch: async (url, options = {}) => {
    calls.push({ url, options });
    responseCount += 1;
    if (url === "/api/training/tasks/generate-from-report") {
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
                status: "todo",
                priority: "high",
                masteryScore: 45,
                attemptCount: 0,
              },
            ],
          };
        },
      };
    }
    if (url === "/api/training/tasks") {
      return {
        ok: true,
        status: 200,
        async json() {
          return { items: [] };
        },
      };
    }
    return {
      ok: true,
      status: 200,
      async json() {
        return {
          stage: "????????",
          stability: "????",
          focus: "RAG ??????",
          prompt: "Explain FastAPI RAG flow",
          decisionSummary: "学习辅导模式：上一轮回答偏弱，先降低难度并给出基础追问。",
          ragReasons: [
            "这道题围绕「RAG 召回链路」展开，主要参考了岗位知识库中的「RAG 基础流程」。",
            "这道题参考了题库中的「RAG 质量评估题」。",
          ],
          agentDecision: {
            nextAction: "switch_topic",
            agentMode: "coach",
            difficulty: "basic",
            focus: "rag_basic",
            reason: "上一轮回答较弱，先换到更基础的 RAG 概念。",
            selectedTrainingTask: {
              weakTag: "rag_quality",
              title: "RAG 质量评估专项训练",
              priority: "high",
            },
            toolCalls: [
              {
                toolName: "retrieve_role_knowledge",
                outputSummary: { hitCount: 2 },
              },
              {
                toolName: "retrieve_question_bank",
                outputSummary: { hitCount: 1 },
              },
            ],
            triggerRules: ["weak_answer_streak", "topic_shift"],
            guardrailApplied: true,
            topicShift: { from: "rag_log_json", to: "rag_basic" },
            debugSignals: {
              weakAnswerStreak: 2,
              repeatedQuestionCount: 1,
              topicLocked: false,
              guardrailApplied: true,
              topicShifted: true,
              triggerRules: ["weak_answer_streak", "topic_shift"],
            },
            policy: {
              policyReasons: ["连续两轮答不上来，coach 模式先解释再追问。"],
              shouldExplainBeforeAsk: true,
              shouldAskUserChoice: true,
              requiresHumanReview: false,
            },
          },
        };
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
  authState.user = { id: 1, email: "student@example.com", username: "student" };
  session.profile = { targetRole: "AI ???????" };
  session.depth = "standard";
  session.selectedProfileId = 77;
  session.currentIndex = 0;
  session.questions = [{ stage: "????", stability: "????", prompt: "Explain FastAPI RAG flow" }];
  agentModeInput.value = "coach";
  answerInput.value = "";
  await goNext();
  const blockedIndex = session.currentIndex;
  const blockedCalls = globalThis.calls.length;
  answerInput.value = "??? FastAPI RAG ???";
  await goNext();
  const repeatedFallbackQuestion = session.questions[1];
  const currentIndexAfterFirstAdvance = session.currentIndex;

  session.currentIndex = 1;
  session.questions[1] = { stage: "项目背景", stability: "自然追问", focus: "RAG 召回链路", prompt: "Explain RAG log JSON" };
  session.answers[0] = { stage: "????", focus: "RAG 召回链路", question: "Explain FastAPI RAG flow", answer: "不会" };
  answerInput.value = "不知道";
  await goNext();
  session.answers = [
    {
      stage: "技术追问",
      focus: "RAG 召回链路",
      question: "请解释 RAG 命中日志怎么设计？",
      answer: "不知道"
    }
  ];
  renderReport(
    {
      score: 52,
      strengths: ["能说出字段含义"],
      risks: ["缺少 JSON 示例"],
      actions: ["准备日志示例"],
      questionReviews: [
        {
          index: 1,
          focus: "RAG 召回链路",
          question: "请解释 RAG 命中日志怎么设计？",
          answerStatus: "不会",
          whyAsked: "用于确认你是否理解 RAG 可观测性。",
          missingPoints: ["字段结构", "质量评分"],
          referenceDirection: "按 query、retriever、hits、quality 说明。",
          trainingAction: "写一条合法 JSON 日志并解释字段。",
          weakTags: ["rag_quality"]
        }
      ],
      trainingPlan: {
        weakTopics: [
          {
            focus: "RAG 召回链路",
            reason: "缺少 JSON 字段结构和质量评分说明。",
            trainingAction: "写一条合法 JSON 日志并解释字段。",
            weakTags: ["rag_quality"]
          }
        ],
        nextRoundPriority: ["RAG 召回链路"],
        practiceQuestions: ["请用 1 分钟说明 RAG 命中日志为什么能提升可观测性。"],
        oneMinuteTemplates: ["背景：排查 RAG 质量；做法：记录 query、hits、quality；结果：定位召回问题。"],
        shouldRetry: true
      }
    },
    "测试报告"
  );
  const preRetrySnapshot = {
    currentIndex: session.currentIndex,
    nextQuestion: repeatedFallbackQuestion,
    switchedQuestion: session.questions[2],
    requestBody: JSON.parse(globalThis.calls[0].options.body),
    answerStatus: answerInput.dataset.status || "",
    agentDecisionHtml: agentDecisionPanel.innerHTML,
    conversationHtml: conversationList.innerHTML,
    stageStepperHtml: stageStepper.innerHTML,
    reportReviewHtml: reportContent.innerHTML,
  };
  const retryPlan = session.latestReport.trainingPlan;
  await startWeakTopicRetry(retryPlan);
  const retryQuestionCalls = globalThis.calls.filter((call) => call.url === "/api/interview/next-question");
  const trainingTaskCall = globalThis.calls.find((call) => call.url === "/api/training/tasks/generate-from-report");
  const trainingLoadCall = globalThis.calls.find((call) => call.url === "/api/training/tasks");
  const retryRequestBody = JSON.parse(retryQuestionCalls.at(-1).options.body);
  globalThis.__result = {
    blockedIndex,
    blockedCalls,
    currentIndexAfterFirstAdvance,
    currentIndex: preRetrySnapshot.currentIndex,
    nextQuestion: preRetrySnapshot.nextQuestion,
    switchedQuestion: preRetrySnapshot.switchedQuestion,
    requestBody: preRetrySnapshot.requestBody,
    answerStatus: preRetrySnapshot.answerStatus,
    agentDecisionHtml: preRetrySnapshot.agentDecisionHtml,
    conversationHtml: preRetrySnapshot.conversationHtml,
    stageStepperHtml: preRetrySnapshot.stageStepperHtml,
    reportReviewHtml: preRetrySnapshot.reportReviewHtml,
    retryDepth: depthInput.value,
    retryMode: modeInput.value,
    retryAgentMode: agentModeInput.value,
    retryRequestBody,
    trainingTaskBody: trainingTaskCall ? JSON.parse(trainingTaskCall.options.body) : null,
    trainingTaskMethod: trainingTaskCall?.options.method || "",
    trainingLoadMethod: trainingLoadCall?.options.method || "",
  };
})()
`;

await vm.runInNewContext(`${appCode}\n${testCode}`, context, { filename: "app.js" });

assert.equal(context.__result.blockedIndex, 0);
assert.equal(context.__result.blockedCalls, 0);
assert.equal(context.__result.currentIndexAfterFirstAdvance, 1);
assert.equal(context.__result.nextQuestion.stage, "项目背景");
assert.equal(context.__result.nextQuestion.focus, "RAG 召回链路");
assert.notEqual(context.__result.switchedQuestion.focus, "RAG 召回链路");
assert.match(context.__result.switchedQuestion.prompt, /换个角度|后端|部署|数据库|项目/);
assert.equal(context.__result.requestBody.applicationProfileId, 77);
assert.equal(context.__result.requestBody.nextStage, "项目背景");
assert.equal(context.__result.requestBody.agentMode, "coach");
assert.notEqual(context.__result.nextQuestion.prompt, "Explain FastAPI RAG flow");
assert.match(context.__result.agentDecisionHtml, /学习辅导模式/);
assert.match(context.__result.agentDecisionHtml, /switch_topic/);
assert.match(context.__result.agentDecisionHtml, /为什么这样问/);
assert.match(context.__result.agentDecisionHtml, /切换话题/);
assert.match(context.__result.agentDecisionHtml, /RAG 质量评估专项训练/);
assert.match(context.__result.agentDecisionHtml, /岗位知识库/);
assert.match(context.__result.agentDecisionHtml, /开发者调试/);
assert.match(context.__result.agentDecisionHtml, /agent-insight-grid/);
assert.match(context.__result.agentDecisionHtml, /考察点/);
assert.match(context.__result.agentDecisionHtml, /触发规则/);
assert.match(context.__result.agentDecisionHtml, /Agent 调试面板/);
assert.match(context.__result.agentDecisionHtml, /保护规则/);
assert.match(context.__result.agentDecisionHtml, /已介入/);
assert.match(context.__result.agentDecisionHtml, /连续弱回答/);
assert.match(context.__result.agentDecisionHtml, /重复问题/);
assert.match(context.__result.agentDecisionHtml, /话题迁移/);
assert.match(context.__result.agentDecisionHtml, /rag_log_json/);
assert.match(context.__result.agentDecisionHtml, /rag_basic/);
assert.match(context.__result.agentDecisionHtml, /weak_answer_streak/);
assert.doesNotMatch(context.__result.agentDecisionHtml, /undefined/);
assert.match(context.__result.agentDecisionHtml, /追问依据/);
assert.match(context.__result.agentDecisionHtml, /RAG 基础流程/);
assert.match(context.__result.agentDecisionHtml, /策略原因/);
assert.match(context.__result.agentDecisionHtml, /先解释再追问/);
assert.match(context.__result.agentDecisionHtml, /建议让用户选择/);
assert.match(context.__result.conversationHtml, /AI 面试官 · RAG 召回链路/);
assert.match(context.__result.conversationHtml, /conversation-message interviewer-message/);
assert.match(context.__result.conversationHtml, /message-bubble/);
assert.doesNotMatch(context.__result.stageStepperHtml, />项目背景</);
assert.match(context.__result.stageStepperHtml, /compact-progress/);
assert.match(context.__result.stageStepperHtml, /progress-dot/);
assert.doesNotMatch(context.__result.stageStepperHtml, /\[object Object\]/);
assert.match(context.__result.reportReviewHtml, /逐题学习复盘/);
assert.match(context.__result.reportReviewHtml, /RAG 召回链路/);
assert.match(context.__result.reportReviewHtml, /用于确认你是否理解 RAG 可观测性/);
assert.match(context.__result.reportReviewHtml, /写一条合法 JSON 日志/);
assert.match(context.__result.reportReviewHtml, /下一轮训练计划/);
assert.match(context.__result.reportReviewHtml, /请用 1 分钟说明 RAG 命中日志/);
assert.match(context.__result.reportReviewHtml, /建议重练/);
assert.match(context.__result.reportReviewHtml, /一键重练薄弱点/);
assert.equal(context.__result.retryDepth, "quick");
assert.equal(context.__result.retryMode, "技术一面");
assert.equal(context.__result.retryAgentMode, "coach");
assert.equal(context.__result.retryRequestBody.agentMode, "coach");
assert.match(context.__result.retryRequestBody.profile.company, /下一轮复练重点：RAG 召回链路/);
assert.match(context.__result.retryRequestBody.profile.company, /请用 1 分钟说明 RAG 命中日志/);
assert.equal(context.__result.trainingTaskMethod, "POST");
assert.equal(context.__result.trainingLoadMethod, "GET");
assert.equal(context.__result.trainingTaskBody.applicationProfileId, 77);
assert.match(JSON.stringify(context.__result.trainingTaskBody.report), /rag_quality/);
