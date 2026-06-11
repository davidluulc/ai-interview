const setupForm = document.querySelector("#setupForm");
const candidateNameInput = document.querySelector("#candidateNameInput");
const targetRoleInput = document.querySelector("#targetRoleInput");
const matchPositionButton = document.querySelector("#matchPositionButton");
const positionAgentResult = document.querySelector("#positionAgentResult");
const applicationTypeInput = document.querySelector("#applicationTypeInput");
const resumeFileInput = document.querySelector("#resumeFileInput");
const parseResumeButton = document.querySelector("#parseResumeButton");
const resumeParseStatus = document.querySelector("#resumeParseStatus");
const resumeInput = document.querySelector("#resumeInput");
const jdInput = document.querySelector("#jdInput");
const companyInput = document.querySelector("#companyInput");
const modeInput = document.querySelector("#modeInput");
const agentModeInput = document.querySelector("#agentModeInput");
const depthInput = document.querySelector("#depthInput");
const emptyState = document.querySelector("#emptyState");
const interviewState = document.querySelector("#interviewState");
const sessionTitle = document.querySelector("#sessionTitle");
const progressText = document.querySelector("#progressText");
const stageLabel = document.querySelector("#stageLabel");
const stabilityLabel = document.querySelector("#stabilityLabel");
const questionText = document.querySelector("#questionText");
const answerInput = document.querySelector("#answerInput");
const answerStatus = document.querySelector("#answerStatus");
const agentDecisionPanel = document.querySelector("#agentDecisionPanel");
const nextButton = document.querySelector("#nextButton");
const reportButton = document.querySelector("#reportButton");
const reportPanel = document.querySelector("#reportPanel");
const reportContent = document.querySelector("#reportContent");
const reportSaveStatus = document.querySelector("#reportSaveStatus");
const retrySaveButton = document.querySelector("#retrySaveButton");
const sourceBadge = document.querySelector("#sourceBadge");
const stageStepper = document.querySelector("#stageStepper");
const conversationList = document.querySelector("#conversationList");
const historyStats = document.querySelector("#historyStats");
const historyList = document.querySelector("#historyList");
const reviewPanel = document.querySelector("#reviewPanel");
const clearHistoryButton = document.querySelector("#clearHistoryButton");
const ragDebugButton = document.querySelector("#ragDebugButton");
const ragLogButton = document.querySelector("#ragLogButton");
const ragDebugContent = document.querySelector("#ragDebugContent");
const ragLogContent = document.querySelector("#ragLogContent");
const agentLogButton = document.querySelector("#agentLogButton");
const agentLogContent = document.querySelector("#agentLogContent");
const ragDocumentForm = document.querySelector("#ragDocumentForm");
const ragDocumentTitleInput = document.querySelector("#ragDocumentTitleInput");
const ragKnowledgeBaseInput = document.querySelector("#ragKnowledgeBaseInput");
const ragDocumentContentInput = document.querySelector("#ragDocumentContentInput");
const ragDocumentMetadataInput = document.querySelector("#ragDocumentMetadataInput");
const ragDocumentSubmitButton = document.querySelector("#ragDocumentSubmitButton");
const ragDocumentRefreshButton = document.querySelector("#ragDocumentRefreshButton");
const ragDocumentStatus = document.querySelector("#ragDocumentStatus");
const ragDocumentList = document.querySelector("#ragDocumentList");
const ragDocumentDetail = document.querySelector("#ragDocumentDetail");
const userCenterSummary = document.querySelector("#userCenterSummary");
const profileStatus = document.querySelector("#profileStatus");
const profileList = document.querySelector("#profileList");
const saveProfileButton = document.querySelector("#saveProfileButton");
const trainingRefreshButton = document.querySelector("#trainingRefreshButton");
const trainingTaskList = document.querySelector("#trainingTaskList");
const trainingTaskDetail = document.querySelector("#trainingTaskDetail");
const adminNavButton = document.querySelector("#adminNavButton");
const adminDashboardPanel = document.querySelector("#adminDashboardPanel");
const adminRefreshButton = document.querySelector("#adminRefreshButton");
const adminDashboardContent = document.querySelector("#adminDashboardContent");
const productNav = document.querySelector("#productNav");
const authSummary = document.querySelector("#authSummary");
const authForm = document.querySelector("#authForm");
const authEmailInput = document.querySelector("#authEmailInput");
const authUsernameInput = document.querySelector("#authUsernameInput");
const authPasswordInput = document.querySelector("#authPasswordInput");
const authSubmitButton = document.querySelector("#authSubmitButton");
const loginTabButton = document.querySelector("#loginTabButton");
const registerTabButton = document.querySelector("#registerTabButton");
const logoutButton = document.querySelector("#logoutButton");
const authStatus = document.querySelector("#authStatus");
const authCard = document.querySelector(".auth-card");

const historyStorageKey = "aiMockInterviewHistory";
const authStorageKey = "aiMockInterviewAuth";
let authMode = "login";

const session = {
  currentIndex: 0,
  profile: null,
  resumeFileName: "",
  positionTag: "",
  questions: [],
  answers: [],
  usingModel: false,
  savedReportId: null,
  latestReport: null,
  selectedProfileId: null,
  latestAgentDecision: null,
  training: {
    tasks: [],
    selectedTaskId: null,
  },
  admin: {
    summary: null,
    users: [],
    documents: [],
    ragLogs: [],
    ragQuality: null,
    agentLogs: [],
  },
};

const authState = {
  accessToken: "",
  refreshToken: "",
  user: null,
};
let refreshPromise = null;
let applicationProfiles = [];
let ragDocuments = [];
let currentHistory = [];

function switchProductSection(sectionName = "interview-workbench") {
  if (typeof document.querySelectorAll !== "function") {
    return;
  }

  const targetName = sectionName || "interview-workbench";
  document.querySelectorAll("[data-product-section]").forEach((section) => {
    const isTarget = section.dataset.productSection === targetName;
    section.classList.toggle("is-active", isTarget);
  });
  document.querySelectorAll("[data-section-target]").forEach((button) => {
    const isTarget = button.dataset.sectionTarget === targetName;
    button.classList.toggle("is-active", isTarget);
    button.setAttribute("aria-current", isTarget ? "page" : "false");
  });
}

function bindProductNavigation() {
  if (!productNav) {
    return;
  }

  productNav.addEventListener("click", (event) => {
    const button = event.target.closest("[data-section-target]");
    if (!button) {
      return;
    }
    switchProductSection(button.dataset.sectionTarget);
  });
}

const interviewStages = [
  { stage: "自我介绍", stability: "自然表达" },
  { stage: "项目深挖", stability: "自然追问" },
  { stage: "技术问答", stability: "稳定评分" },
  { stage: "行为面试", stability: "结构化判断" },
  { stage: "薪资与规划", stability: "稳定建议" },
];

const stagePlans = {
  quick: interviewStages,
  standard: [
    { stage: "自我介绍", stability: "自然表达" },
    { stage: "项目背景", stability: "自然追问" },
    { stage: "项目职责", stability: "自然追问" },
    { stage: "技术基础", stability: "稳定评分" },
    { stage: "技术追问", stability: "稳定评分" },
    { stage: "场景问题", stability: "结构化判断" },
    { stage: "行为面试", stability: "结构化判断" },
    { stage: "薪资与规划", stability: "稳定建议" },
  ],
  deep: [
    { stage: "自我介绍", stability: "自然表达" },
    { stage: "简历风险", stability: "结构化判断" },
    { stage: "项目背景", stability: "自然追问" },
    { stage: "项目职责", stability: "自然追问" },
    { stage: "项目难点", stability: "自然追问" },
    { stage: "技术基础", stability: "稳定评分" },
    { stage: "技术追问", stability: "稳定评分" },
    { stage: "系统设计", stability: "稳定评分" },
    { stage: "场景问题", stability: "结构化判断" },
    { stage: "行为面试", stability: "结构化判断" },
    { stage: "反问准备", stability: "自然表达" },
    { stage: "薪资与规划", stability: "稳定建议" },
  ],
};

function getActiveStages() {
  return stagePlans[session.depth || "standard"];
}

function summarize(text, fallback) {
  const clean = String(text || "").trim().replace(/\s+/g, " ");
  if (!clean) {
    return fallback;
  }

  return clean.length > 36 ? `${clean.slice(0, 36)}...` : clean;
}

function inferKeyword(text, fallback) {
  const candidates = [
    "Java",
    "Spring",
    "Redis",
    "MySQL",
    "React",
    "Vue",
    "Python",
    "算法",
    "测试",
    "产品",
    "项目",
    "实习",
  ];
  const found = candidates.find((word) => text.toLowerCase().includes(word.toLowerCase()));
  return found || fallback;
}

function inferQuestionFocus(question = {}) {
  const text = `${question.focus || ""} ${question.prompt || ""} ${question.stage || ""}`;
  const focusRules = [
    { pattern: /RAG|召回|检索|重排|chunk|切片|知识库/i, label: "RAG 召回链路" },
    { pattern: /FastAPI|接口|路由|后端|模块|SQLAlchemy/i, label: "后端模块设计" },
    { pattern: /简历|真实性|经历|负责|项目/i, label: "项目经历核验" },
    { pattern: /部署|Docker|Nginx|云服务器|上线/i, label: "部署上线理解" },
    { pattern: /Redis|MySQL|数据库|事务|缓存/i, label: "数据库与缓存" },
    { pattern: /薪资|到岗|规划|期望/i, label: "求职规划表达" },
  ];
  return focusRules.find((rule) => rule.pattern.test(text))?.label || question.focus || question.stage || "综合追问";
}

function normalizeQuestion(question, stagePlan = {}) {
  const normalizedFocus = inferQuestionFocus(question);
  return {
    stage: question.stage || stagePlan.stage || "动态追问",
    stability: question.stability || stagePlan.stability || "自然追问",
    focus: normalizedFocus,
    prompt: question.prompt || "",
    agentDecision: question.agentDecision || {},
    decisionSummary: question.decisionSummary || "",
    ragReasons: Array.isArray(question.ragReasons) ? question.ragReasons : [],
  };
}

function attachAgentDecision(question, source = {}) {
  const questionDecision =
    question.agentDecision && Object.keys(question.agentDecision).length > 0 ? question.agentDecision : null;
  const questionRagReasons = Array.isArray(question.ragReasons) && question.ragReasons.length > 0 ? question.ragReasons : null;
  return {
    ...question,
    agentDecision: questionDecision || source.agentDecision || {},
    decisionSummary: question.decisionSummary || source.decisionSummary || "",
    ragReasons: questionRagReasons || source.ragReasons || [],
  };
}

function normalizeTextForCompare(text = "") {
  return text.replace(/\s+/g, "").replace(/[，。！？、,.!?]/g, "").toLowerCase();
}

function isRepeatedPrompt(prompt, questions = []) {
  const current = normalizeTextForCompare(prompt);
  if (!current) {
    return false;
  }
  return questions.some((question) => {
    const previous = normalizeTextForCompare(question?.prompt || "");
    return previous && (previous === current || previous.includes(current) || current.includes(previous));
  });
}

function isWeakAnswer(answer = "") {
  const text = String(answer || "").trim();
  if (!text) {
    return true;
  }
  if (text.length <= 8 && /(不会|不知道|不清楚|写不出来|答不上|没做过|不了解)/.test(text)) {
    return true;
  }
  return /(不会写|写不出来|不知道啊|连.*都不知道|无法.*说出来|答不上来)/.test(text);
}

function countRecentSameFocus(focus, answers = []) {
  let count = 0;
  for (let index = answers.length - 1; index >= 0; index -= 1) {
    if (answers[index]?.focus !== focus) {
      break;
    }
    count += 1;
  }
  return count;
}

function shouldSwitchFocus(candidateQuestion, answers = []) {
  const sameFocusCount = countRecentSameFocus(candidateQuestion.focus, answers);
  const recentWeakCount = answers.slice(-2).filter((answer) => isWeakAnswer(answer?.answer)).length;
  return sameFocusCount >= 2 || (sameFocusCount >= 1 && recentWeakCount >= 2);
}

function nextAlternativeFocus(currentFocus, profile = {}) {
  const text = `${profile.resume || ""} ${profile.jd || ""} ${profile.company || ""}`;
  const candidates = [
    { focus: "后端模块设计", pattern: /FastAPI|接口|后端|SQLAlchemy|路由/i },
    { focus: "数据库与缓存", pattern: /MySQL|Redis|数据库|缓存|SQL/i },
    { focus: "部署上线理解", pattern: /Docker|Nginx|云服务器|部署|上线/i },
    { focus: "项目经历核验", pattern: /项目|负责|简历|经历/i },
    { focus: "求职规划表达", pattern: /岗位|公司|到岗|规划|实习/i },
  ];
  return (
    candidates.find((item) => item.focus !== currentFocus && item.pattern.test(text))?.focus ||
    candidates.find((item) => item.focus !== currentFocus)?.focus ||
    "综合追问"
  );
}

function buildSwitchFocusQuestion(profile, index, currentFocus) {
  const nextStage = getActiveStages()[index] || {};
  const focus = nextAlternativeFocus(currentFocus, profile);
  const prompts = {
    后端模块设计: "换个角度聊后端实现：这个项目里 FastAPI 后端主要拆成哪些模块？每个模块负责什么？",
    数据库与缓存: "换个角度聊数据层：这个项目哪些数据需要持久化？如果引入 MySQL 和 Redis，你会分别存什么？",
    部署上线理解: "换个角度聊上线：如果把这个系统部署到云服务器，你会如何安排 Docker、Nginx、环境变量和日志？",
    项目经历核验: "换个角度聊项目真实性：这个系统里哪些模块是你最熟悉的？请讲一个你能从代码层面解释清楚的模块。",
    求职规划表达: "换个角度聊求职表达：如果面试官质疑你某个技术点不熟，你会如何诚实说明边界并展示学习计划？",
  };
  return normalizeQuestion(
    {
      stage: nextStage.stage || "动态追问",
      stability: nextStage.stability || "自然追问",
      focus,
      prompt: prompts[focus] || `换个角度继续聊：请避开「${currentFocus}」，讲一个你更能解释清楚的项目模块。`,
    },
    nextStage
  );
}

function buildFocusedFallbackQuestion(profile, index, previousAnswer = {}) {
  const base = buildFallbackQuestion(profile, index);
  const answerText = previousAnswer.answer || "";
  const focus = inferQuestionFocus({ ...base, prompt: `${base.prompt} ${answerText}` });
  const topic = summarize(answerText, "你上一轮回答里提到的内容");
  const prompts = {
    "RAG 召回链路": `你刚才提到「${topic}」。请具体说明这套 RAG 链路里 query 怎么构造、如何判断命中质量，以及命中不准时你会怎么排查？`,
    后端模块设计: `你刚才提到「${topic}」。请具体说明这个后端模块的输入输出、数据库交互和异常处理是怎么设计的？`,
    项目经历核验: `围绕你刚才说的「${topic}」，请说明哪些部分是你独立完成的，遇到的最大困难是什么，最后怎么验证效果？`,
    部署上线理解: `如果要把你刚才说的内容上线到云服务器，请按顺序讲一下部署链路、环境变量、Nginx 反向代理和日志排查。`,
    数据库与缓存: `你刚才提到「${topic}」。请说明数据表或缓存 key 怎么设计，如何保证数据一致性和异常兜底？`,
  };
  return normalizeQuestion(
    {
      ...base,
      focus,
      prompt: prompts[focus] || `你刚才提到「${topic}」。请补充一个更具体的技术细节：当时你怎么做、为什么这么做、怎么验证它有效？`,
    },
    getActiveStages()[index]
  );
}

function buildQuestions(profile) {
  const resumePoint = summarize(profile.resume, "你简历中最有代表性的经历");
  const jdPoint = summarize(profile.jd, "目标岗位的核心要求");
  const companyPoint = summarize(profile.company, "公司对候选人的期待");
  const keyword = inferKeyword(`${profile.resume} ${profile.jd}`, "岗位核心技能");

  return [
    {
      stage: "自我介绍",
      stability: "自然表达",
      focus: "表达动机与匹配度",
      prompt: `请你先做一个 1 分钟左右的自我介绍，重点结合「${resumePoint}」和你为什么想投递这个岗位。`,
    },
    {
      stage: "项目深挖",
      stability: "自然追问",
      focus: "项目经历核验",
      prompt: `我注意到你的经历里提到了「${resumePoint}」。请你讲一下这个经历的背景、你负责的部分，以及最后产生了什么结果。`,
    },
    {
      stage: "技术问答",
      stability: "稳定评分",
      focus: "核心技术理解",
      prompt: `结合岗位要求「${jdPoint}」，请你解释一下你对「${keyword}」的理解，并说说你在项目里是怎么使用或学习它的。`,
    },
    {
      stage: "行为面试",
      stability: "结构化判断",
      focus: "协作与抗压",
      prompt: `如果你在项目协作中遇到进度压力，或者和同学/同事意见不一致，你通常会怎么处理？请结合一个真实例子回答。`,
    },
    {
      stage: "薪资与规划",
      stability: "稳定建议",
      focus: "求职规划表达",
      prompt: `结合「${companyPoint}」，请你说说你对这份岗位的期待、到岗时间，以及你未来 1 年希望提升的能力。`,
    },
  ];
}

function buildFallbackQuestion(profile, index) {
  const baseQuestions = buildQuestions(profile);
  const activeStage = getActiveStages()[index];

  if (baseQuestions[index]) {
    return {
      ...baseQuestions[index],
      stage: activeStage.stage,
      stability: activeStage.stability,
    };
  }

  const resumePoint = summarize(profile.resume, "你简历中最有代表性的经历");
  const jdPoint = summarize(profile.jd, "目标岗位的核心要求");
  const prompts = {
    简历风险: `你的简历里「${resumePoint}」这部分如果被面试官质疑真实性或深度，你会怎么证明？`,
    项目背景: `请你补充说明「${resumePoint}」这个经历的业务背景、用户是谁，以及为什么要做。`,
    项目职责: "请你具体说说这个项目中哪些模块是你独立负责的，哪些是协作完成的。",
    项目难点: "这个项目里你遇到的最大技术难点是什么？你当时尝试过哪些解决方案？",
    技术基础: `结合岗位要求「${jdPoint}」，请你解释一个你最熟悉的核心技术点。`,
    技术追问: "如果让你把这个技术点讲给一个刚入门的同学，你会怎么解释原理和使用场景？",
    系统设计: "如果这个项目用户量增长 10 倍，你会优先优化哪些部分？为什么？",
    场景问题: "如果线上接口突然变慢，你会按什么顺序排查？请说出具体步骤。",
    反问准备: "面试最后如果让你反问面试官，你会问哪两个问题？为什么？",
  };

  return {
    stage: activeStage.stage,
    stability: activeStage.stability,
    focus: inferQuestionFocus({ stage: activeStage.stage, prompt: prompts[activeStage.stage] || "" }),
    prompt: prompts[activeStage.stage] || `请围绕「${activeStage.stage}」继续补充一个具体例子。`,
  };
}

function loadAuthState() {
  try {
    const saved = JSON.parse(localStorage.getItem(authStorageKey)) || {};
    authState.accessToken = saved.accessToken || "";
    authState.refreshToken = saved.refreshToken || "";
    authState.user = saved.user || null;
  } catch {
    clearAuthState();
  }
}

function saveAuthState() {
  localStorage.setItem(
    authStorageKey,
    JSON.stringify({
      accessToken: authState.accessToken,
      refreshToken: authState.refreshToken,
      user: authState.user,
    })
  );
}

function clearAuthState() {
  authState.accessToken = "";
  authState.refreshToken = "";
  authState.user = null;
  localStorage.removeItem(authStorageKey);
}

function isLoggedIn() {
  return Boolean(authState.accessToken && authState.user);
}

function authHeaders(extra = {}) {
  const headers = { ...extra };
  if (authState.accessToken) {
    headers.Authorization = `Bearer ${authState.accessToken}`;
  }
  return headers;
}

function renderAuthState() {
  if (isLoggedIn()) {
    authCard.classList.add("is-logged-in");
    authSummary.innerHTML = `
      <span class="auth-state-pill">已登录</span>
      <strong>${authState.user.username}</strong>
      <small>${authState.user.email}</small>
    `;
    authForm.classList.add("hidden");
    logoutButton.classList.remove("hidden");
    authStatus.textContent = "已登录，历史记录会保存到你的账号。";
  } else {
    authCard.classList.remove("is-logged-in");
    authSummary.innerHTML = `
      <span class="auth-state-pill muted">未登录</span>
      <strong>账号中心</strong>
      <small>登录后保存云端面试记录</small>
    `;
    authForm.classList.remove("hidden");
    logoutButton.classList.add("hidden");
    authStatus.textContent = "登录后可保存和查看自己的面试记录。";
  }
  authUsernameInput.classList.toggle("hidden", authMode !== "register");
  authSubmitButton.textContent = authMode === "register" ? "注册" : "登录";
  loginTabButton.classList.toggle("active", authMode === "login");
  registerTabButton.classList.toggle("active", authMode === "register");
  renderAdminVisibility();
}

function buildJsonHeaders(options = {}) {
  return {
    "Content-Type": "application/json",
    ...(options.auth ? authHeaders() : {}),
  };
}

async function readResponseError(response) {
  const detail = await response.json().catch(() => ({}));
  return new Error(detail.error?.message || detail.detail || `Request failed: ${response.status}`);
}

async function refreshAccessToken() {
  if (!authState.refreshToken) {
    return false;
  }

  if (!refreshPromise) {
    refreshPromise = fetch("/api/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refreshToken: authState.refreshToken }),
    })
      .then(async (response) => {
        if (!response.ok) {
          throw await readResponseError(response);
        }
        return response.json();
      })
      .then((result) => {
        authState.accessToken = result.accessToken;
        authState.user = result.user;
        saveAuthState();
        renderAuthState();
        authStatus.textContent = "登录状态已自动续期。";
        return true;
      })
      .catch((error) => {
        console.warn("Token refresh failed:", error);
        clearAuthState();
        renderAuthState();
        authStatus.textContent = "登录已过期，请重新登录。";
        return false;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

async function authFetch(url, options = {}, retryOnUnauthorized = true) {
  const headers = authHeaders(options.headers || {});
  const response = await fetch(url, { ...options, headers });

  if (response.status !== 401 || !retryOnUnauthorized) {
    return response;
  }

  const refreshed = await refreshAccessToken();
  if (!refreshed) {
    return response;
  }

  return authFetch(url, options, false);
}

async function requestJson(url, payload, options = {}) {
  const fetcher = options.auth ? authFetch : fetch;
  const response = await fetcher(url, {
    method: "POST",
    headers: buildJsonHeaders(options),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw await readResponseError(response);
  }

  return response.json();
}

async function requestGetJson(url, options = {}) {
  const fetcher = options.auth ? authFetch : fetch;
  const response = await fetcher(url, {
    method: "GET",
    headers: options.auth ? authHeaders(options.headers || {}) : options.headers || {},
  });

  if (!response.ok) {
    throw await readResponseError(response);
  }

  return response.json();
}

function isAdminUser() {
  return authState.user?.role === "admin";
}

function renderAdminVisibility() {
  if (!adminNavButton) {
    return;
  }

  if (isAdminUser()) {
    adminNavButton.classList.remove("hidden");
  } else {
    adminNavButton.classList.add("hidden");
    adminDashboardPanel?.classList.add("hidden");
  }
}

function adminSummaryCard(label, value) {
  return `
    <article>
      <span>${label}</span>
      <strong>${value ?? 0}</strong>
    </article>
  `;
}

function adminListSection(title, items, renderItem) {
  const content = items.length ? items.map(renderItem).join("") : "<p>暂无数据</p>";
  return `
    <section class="admin-list-section">
      <h3>${title}</h3>
      ${content}
    </section>
  `;
}

function formatRagQualityIssue(issueType) {
  const labels = {
    empty_recall: "空召回",
    weak_recall: "弱召回",
    unused_in_prompt: "未进入 Prompt",
  };
  return labels[issueType] || issueType || "未知问题";
}

function renderAdminRagQuality(quality = {}) {
  const summary = quality.summary || {};
  const items = Array.isArray(quality.items) ? quality.items.slice(0, 5) : [];
  const issueCards = [
    { label: "空召回", value: summary.emptyRecallCount ?? 0, hint: "检索没有拿到任何 chunk，优先补知识库或改 query rewrite。" },
    { label: "弱召回", value: summary.weakRecallCount ?? 0, hint: "命中质量偏低，关注关键词覆盖率和 rerank 分数。" },
    { label: "未进入 Prompt", value: summary.unusedInPromptCount ?? 0, hint: "召回到了内容但没有进入提示词，检查截断和筛选规则。" },
  ];
  const content = items.length
    ? items
        .map(
          (item) => `
            <article class="admin-quality-sample">
              <strong>${formatRagQualityIssue(item.issueType)}</strong>
              <p>${item.retrieverName || "retriever"} · ${item.queryText || "空查询"}</p>
              <span>建议动作：${item.recommendation || item.quality?.reason || "暂无建议"}</span>
            </article>
          `
        )
        .join("")
    : "<p class=\"helper-text\">暂无低质量召回。</p>";
  return `
    <section class="admin-list-section admin-rag-quality-section">
      <h3>低质量召回</h3>
      <p>总计 ${summary.lowQualityCount ?? 0} 条低质量记录，用于定位 RAG 召回链路的薄弱环节。</p>
      <h4>质量问题分布</h4>
      <div class="admin-quality-grid">
        ${issueCards
          .map(
            (card) => `
              <article>
                <span>${card.label}</span>
                <strong>${card.value}</strong>
                <small>${card.hint}</small>
              </article>
            `
          )
          .join("")}
      </div>
      <h4>建议动作</h4>
      <div class="admin-quality-sample-list">
        ${content}
      </div>
    </section>
  `;
}

function renderAdminDashboard() {
  if (!adminDashboardContent) {
    return;
  }

  const summary = session.admin.summary || {};
  adminDashboardContent.innerHTML = `
    <div class="admin-summary-grid">
      ${adminSummaryCard("用户总数", summary.userCount)}
      ${adminSummaryCard("面试记录", summary.interviewRecordCount)}
      ${adminSummaryCard("RAG 文档", summary.ragDocumentCount)}
      ${adminSummaryCard("RAG 日志", summary.ragRetrievalLogCount)}
      ${adminSummaryCard("Agent 日志", summary.agentDecisionLogCount)}
    </div>
    ${renderAdminRagQuality(session.admin.ragQuality)}
    <div class="admin-list-grid">
      ${adminListSection(
        "用户",
        session.admin.users,
        (user) => `<p>${user.email || "未知邮箱"} · ${user.username || "未知用户"} · ${user.role || "user"}</p>`
      )}
      ${adminListSection(
        "RAG 文档",
        session.admin.documents,
        (document) => `<p>${document.title || "未命名文档"} · ${document.knowledgeBase || "unknown"} · chunk ${document.chunkCount ?? 0}</p>`
      )}
      ${adminListSection(
        "RAG 日志",
        session.admin.ragLogs,
        (log) => `<p>${log.retrieverName || "retriever"} · ${log.queryText || "空查询"} · 命中 ${log.hitCount ?? 0}</p>`
      )}
      ${adminListSection(
        "Agent 日志",
        session.admin.agentLogs,
        (log) => `<p>${log.nextAction || "unknown"} · ${log.focus || "未记录考察点"} · ${log.reason || "未记录原因"}</p>`
      )}
    </div>
  `;
}

async function loadAdminDashboard() {
  if (!isAdminUser()) {
    if (adminDashboardContent) {
      adminDashboardContent.innerHTML = `<p class="empty-state">需要管理员权限。</p>`;
    }
    return;
  }

  const [summary, users, documents, ragLogs, ragQuality, agentLogs] = await Promise.all([
    requestGetJson("/api/admin/summary", { auth: true }),
    requestGetJson("/api/admin/users", { auth: true }),
    requestGetJson("/api/admin/rag/documents", { auth: true }),
    requestGetJson("/api/admin/rag/logs", { auth: true }),
    requestGetJson("/api/admin/rag/quality", { auth: true }),
    requestGetJson("/api/admin/agent/logs", { auth: true }),
  ]);
  session.admin = {
    summary,
    users: Array.isArray(users.items) ? users.items : [],
    documents: Array.isArray(documents.items) ? documents.items : [],
    ragLogs: Array.isArray(ragLogs.items) ? ragLogs.items : [],
    ragQuality,
    agentLogs: Array.isArray(agentLogs.items) ? agentLogs.items : [],
  };
  renderAdminDashboard();
}

async function submitAuth(event) {
  event.preventDefault();
  authSubmitButton.disabled = true;
  authStatus.textContent = authMode === "register" ? "正在注册..." : "正在登录...";

  try {
    if (authMode === "register") {
      await requestJson("/api/auth/register", {
        email: authEmailInput.value,
        username: authUsernameInput.value,
        password: authPasswordInput.value,
      });
      authStatus.textContent = "注册成功，正在登录...";
    }

    const result = await requestJson("/api/auth/login", {
      email: authEmailInput.value,
      password: authPasswordInput.value,
    });
    authState.accessToken = result.accessToken;
    authState.refreshToken = result.refreshToken;
    authState.user = result.user;
    saveAuthState();
    renderAuthState();
    await renderHistory();
    await renderUserCenter();
    await loadTrainingTasks();
  } catch (error) {
    console.warn("Auth failed:", error);
    authStatus.textContent = `认证失败：${error.message}`;
  } finally {
    authSubmitButton.disabled = false;
  }
}

async function logout() {
  if (authState.refreshToken) {
    await requestJson("/api/auth/logout", { refreshToken: authState.refreshToken }).catch((error) => {
      console.warn("Logout failed:", error);
    });
  }
  clearAuthState();
  renderAuthState();
  await renderHistory();
  await renderUserCenter();
  await loadTrainingTasks();
}

async function syncCurrentUser() {
  if (!authState.accessToken) {
    renderTrainingCenter();
    return;
  }

  const response = await authFetch("/api/auth/me");
  if (!response.ok) {
    clearAuthState();
    renderAuthState();
    await renderHistory();
    await renderUserCenter();
    await loadTrainingTasks();
    return;
  }

  authState.user = await response.json();
  saveAuthState();
  renderAuthState();
  await loadTrainingTasks();
}

async function parseResumeFile() {
  const file = resumeFileInput.files?.[0];
  if (!file) {
    resumeParseStatus.textContent = "请先选择一份 PDF 或图片简历。";
    return;
  }

  const formData = new FormData();
  formData.append("resume", file);
  parseResumeButton.disabled = true;
  resumeParseStatus.textContent = `正在解析：${file.name}`;

  try {
    const response = await fetch("/api/resume/parse", {
      method: "POST",
      body: formData,
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || `解析失败：${response.status}`);
    }

    session.resumeFileName = result.fileName || file.name;
    resumeInput.value = result.summary || "";
    resumeParseStatus.textContent = `已解析：${session.resumeFileName}`;
  } catch (error) {
    console.warn("Resume parse failed:", error);
    resumeParseStatus.textContent = `解析失败：${error.message}`;
  } finally {
    parseResumeButton.disabled = false;
  }
}

async function matchPositions() {
  const profile = {
    candidateName: candidateNameInput.value,
    targetRole: targetRoleInput.value,
    resume: resumeInput.value,
    jd: jdInput.value,
    company: companyInput.value,
  };

  matchPositionButton.disabled = true;
  positionAgentResult.innerHTML = `<p class="helper-text">岗位匹配 Agent 正在分析...</p>`;

  try {
    const result = await requestJson("/api/position-agent/match", {
      profile,
      targetDirection: targetRoleInput.value,
    });
    const matches = result.matches || [];

    if (!matches.length) {
      positionAgentResult.innerHTML = `<p class="helper-text">暂时没有匹配结果。可以先补充简历亮点或 JD。</p>`;
      return;
    }

    positionAgentResult.innerHTML = matches
      .map(
        (item, index) => `
          <article class="agent-match ${index === 0 ? "best" : ""}">
            <div>
              <strong>${item.title}</strong>
              <p>匹配分：${item.score} · ${item.reason}</p>
              <p>重点追问：${(item.focus_topics || []).slice(0, 3).join("、")}</p>
            </div>
            <button class="secondary-button" type="button" data-position-tag="${item.position_tag}" data-position-title="${item.title}">
              选用
            </button>
          </article>
        `
      )
      .join("");
  } catch (error) {
    console.warn("Position agent failed:", error);
    positionAgentResult.innerHTML = `<p class="helper-text">岗位匹配失败：${error.message}</p>`;
  } finally {
    matchPositionButton.disabled = false;
  }
}

function renderQuestion() {
  const question = normalizeQuestion(session.questions[session.currentIndex], getActiveStages()[session.currentIndex]);
  session.questions[session.currentIndex] = question;
  const total = getActiveStages().length;

  stageLabel.textContent = `考察点：${question.focus}`;
  stabilityLabel.textContent = question.stability;
  questionText.textContent = question.prompt;
  progressText.textContent = `${session.currentIndex + 1} / ${total}`;
  answerInput.value = session.answers[session.currentIndex]?.answer || "";
  answerStatus.textContent = "";
  answerInput.dataset.status = "";
  nextButton.textContent =
    session.currentIndex === total - 1 ? "提交回答，生成报告" : "提交回答，进入下一题";
  renderStageStepper();
  renderConversation();
  renderAgentDecision(question);
}

function agentModeLabel(mode) {
  return mode === "coach" ? "学习辅导模式" : "真实面试模式";
}

function yesNoLabel(value) {
  return value ? "是" : "否";
}

function guardrailLabel(value) {
  return value ? "已介入" : "未介入";
}

function getAgentDebugSignals(source = {}) {
  const signals = source.debugSignals;
  return signals && typeof signals === "object" && !Array.isArray(signals) ? signals : {};
}

function getAgentTriggerRules(decision = {}) {
  const debugSignals = getAgentDebugSignals(decision);
  if (Array.isArray(debugSignals.triggerRules) && debugSignals.triggerRules.length) {
    return debugSignals.triggerRules;
  }
  return Array.isArray(decision.triggerRules) ? decision.triggerRules : [];
}

function getAgentTopicShift(decision = {}) {
  const topicShift = decision.topicShift;
  return topicShift && typeof topicShift === "object" && !Array.isArray(topicShift) ? topicShift : {};
}

function renderRuleTags(rules = []) {
  if (!rules.length) {
    return `<span class="agent-rule-tag muted">暂无触发规则</span>`;
  }
  return rules.map((rule) => `<span class="agent-rule-tag">${rule}</span>`).join("");
}

function renderAgentDebugPanel(decision = {}) {
  const debugSignals = getAgentDebugSignals(decision);
  const triggerRules = getAgentTriggerRules(decision);
  const topicShift = getAgentTopicShift(decision);
  const guardrailApplied = Boolean(decision.guardrailApplied || debugSignals.guardrailApplied);
  const topicShiftText = topicShift.from || topicShift.to ? `${topicShift.from || "未知"} -> ${topicShift.to || "未知"}` : "未发生";
  return `
    <section class="agent-debug-panel-inline" aria-label="Agent 调试面板">
      <div class="agent-debug-title">
        <span>Agent 调试面板</span>
        <strong>可观测性</strong>
      </div>
      <div class="agent-debug-grid">
        <div class="agent-debug-signal">
          <span>保护规则</span>
          <strong>${guardrailLabel(guardrailApplied)}</strong>
        </div>
        <div class="agent-debug-signal">
          <span>连续弱回答</span>
          <strong>${debugSignals.weakAnswerStreak ?? 0}</strong>
        </div>
        <div class="agent-debug-signal">
          <span>重复问题</span>
          <strong>${debugSignals.repeatedQuestionCount ?? 0}</strong>
        </div>
        <div class="agent-debug-signal">
          <span>话题锁定</span>
          <strong>${yesNoLabel(Boolean(debugSignals.topicLocked))}</strong>
        </div>
        <div class="agent-debug-signal">
          <span>话题迁移</span>
          <strong class="agent-topic-shift">${topicShiftText}</strong>
        </div>
        <div class="agent-debug-signal">
          <span>已切换话题</span>
          <strong>${yesNoLabel(Boolean(debugSignals.topicShifted || topicShift.from || topicShift.to))}</strong>
        </div>
      </div>
      <div class="agent-rule-list" aria-label="Agent 触发规则">
        ${renderRuleTags(triggerRules)}
      </div>
    </section>
  `;
}

function agentActionProductLabel(action) {
  const labels = {
    deepen: "继续深挖",
    deep_follow_up: "继续深挖",
    lower_difficulty: "降低难度",
    raise_difficulty: "提高难度",
    switch_topic: "切换话题",
    finish: "结束面试",
    finish_interview: "结束面试",
    summarize_feedback: "阶段反馈",
    coach_explain: "学习辅导",
    select_action: "选择下一步",
  };
  return labels[action] || action || "选择下一步";
}

function agentDifficultyProductLabel(value) {
  const labels = {
    basic: "基础",
    medium: "中等",
    hard: "较难",
    advanced: "进阶",
  };
  return labels[value] || value || "动态";
}

function agentToolReadableName(toolName = "") {
  const name = String(toolName || "");
  if (name.includes("role")) return "岗位知识库";
  if (name.includes("question")) return "题库 RAG";
  if (name.includes("memory") || name.includes("candidate")) return "候选人画像";
  if (name.includes("retrieve")) return "检索工具";
  return name || "工具调用";
}

function renderToolCallChips(toolCalls = []) {
  if (!Array.isArray(toolCalls) || !toolCalls.length) {
    return `<span class="agent-tool-chip muted">暂无工具调用摘要</span>`;
  }
  return toolCalls
    .slice(0, 3)
    .map((tool) => {
      const hitCount = Number(tool.hitCount ?? tool.outputSummary?.hitCount ?? 0);
      return `<span class="agent-tool-chip">${agentToolReadableName(tool.toolName)} · 命中 ${hitCount} 条</span>`;
    })
    .join("");
}

function renderSelectedTrainingTask(task = {}) {
  if (!task || typeof task !== "object" || Array.isArray(task) || !Object.keys(task).length) {
    return "";
  }
  const title = task.title || task.weakLabel || task.weakTag || "专项训练";
  const priority = task.priority ? `优先级：${task.priority}` : "建议本轮后练习";
  return `
    <div class="agent-training-hint">
      <span>推荐训练</span>
      <strong>${title}</strong>
      <small>${priority}</small>
    </div>
  `;
}

function renderAgentPolicyPanel(policy = {}) {
  if (!policy || typeof policy !== "object" || Array.isArray(policy) || !Object.keys(policy).length) {
    return "";
  }
  const reasons = Array.isArray(policy.policyReasons) ? policy.policyReasons.filter(Boolean).slice(0, 3) : [];
  const flags = [
    policy.shouldExplainBeforeAsk ? "先解释再追问" : "",
    policy.shouldAskUserChoice ? "建议让用户选择" : "",
    policy.requiresHumanReview ? "建议人工介入" : "",
  ].filter(Boolean);
  if (!reasons.length && !flags.length) {
    return "";
  }
  return `
    <div class="agent-policy-panel">
      <strong>策略原因</strong>
      ${reasons.length ? `<ul>${reasons.map((reason) => `<li>${reason}</li>`).join("")}</ul>` : ""}
      ${flags.length ? `<div class="agent-policy-flags">${flags.map((flag) => `<span>${flag}</span>`).join("")}</div>` : ""}
    </div>
  `;
}

function renderAgentDecision(question = {}) {
  if (!agentDecisionPanel) {
    return;
  }
  const decision = question.agentDecision || {};
  const summary = question.decisionSummary || decision.decisionSummary || decision.reason || "";
  const ragReasons = Array.isArray(question.ragReasons) ? question.ragReasons : [];
  if (!summary && !decision.nextAction) {
    agentDecisionPanel.innerHTML = "";
    agentDecisionPanel.classList.add("hidden");
    return;
  }

  const rules = getAgentTriggerRules(decision).join(" / ");
  agentDecisionPanel.innerHTML = `
    <div class="agent-product-explain">
      <div class="agent-product-head">
        <span>为什么这样问</span>
        <strong>${agentActionProductLabel(decision.nextAction || "select_action")}</strong>
      </div>
      <p>${summary || "Agent 会根据你的上一轮回答、当前阶段和 RAG 命中内容选择下一题。"}</p>
      <div class="agent-product-meta">
        <span>${agentModeLabel(decision.agentMode || agentModeInput?.value || "interview")}</span>
        <span>考察点：${question.focus || decision.focus || "综合追问"}</span>
        <span>难度：${agentDifficultyProductLabel(decision.difficulty || question.stability)}</span>
      </div>
      <div class="agent-tool-chip-row" aria-label="Agent 参考工具">
        ${renderToolCallChips(decision.toolCalls || [])}
      </div>
      ${renderSelectedTrainingTask(decision.selectedTrainingTask)}
      ${renderAgentPolicyPanel(decision.policy || {})}
      ${
        ragReasons.length
          ? `<div class="rag-reason-list">
              <strong>追问依据</strong>
              <ul>${ragReasons.slice(0, 2).map((reason) => `<li>${reason}</li>`).join("")}</ul>
            </div>`
          : ""
      }
      <details class="agent-debug-details">
        <summary>开发者调试</summary>
        <div class="agent-insight-bar">
          <div class="agent-insight-head">
            <span>${agentModeLabel(decision.agentMode || agentModeInput?.value || "interview")}</span>
            <strong>${decision.nextAction || "select_action"}</strong>
          </div>
          <div class="agent-insight-grid">
            <span>考察点：${question.focus || decision.focus || "综合追问"}</span>
            <span>难度：${decision.difficulty || question.stability || "动态"}</span>
            <span>触发规则：${rules || "未记录"}</span>
          </div>
          ${renderAgentDebugPanel(decision)}
        </div>
      </details>
    </div>
  `;
  agentDecisionPanel.classList.remove("hidden");
}

function renderStageStepper() {
  stageStepper.innerHTML = `
    <div class="compact-progress">
      ${getActiveStages()
        .map((item, index) => {
          const status =
            index < session.currentIndex ? "done" : index === session.currentIndex ? "active" : "pending";
          const stageName = typeof item === "string" ? item : item.stage || `第 ${index + 1} 题`;
          return `
            <div class="progress-step ${status}" aria-label="${stageName}">
              <span class="progress-dot">${index + 1}</span>
              <span class="progress-state">${status === "done" ? "完成" : status === "active" ? "当前" : "待进行"}</span>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderConversation() {
  const items = [];

  session.questions.forEach((question, index) => {
    if (!question) {
      return;
    }

    items.push(`
      <article class="conversation-message interviewer-message">
        <div class="message-avatar">AI</div>
        <div class="message-bubble">
          <span class="message-role">AI 面试官 · ${inferQuestionFocus(question)}</span>
          <p>${question.prompt}</p>
        </div>
      </article>
    `);

    const answer = session.answers[index]?.answer;
    if (answer) {
      items.push(`
        <article class="conversation-message candidate-message">
          <div class="message-avatar">你</div>
          <div class="message-bubble">
            <span class="message-role">候选人回答</span>
            <p>${answer || "未作答"}</p>
          </div>
        </article>
      `);
    }
  });

  conversationList.innerHTML = items.join("");
}

async function startInterview(event) {
  event.preventDefault();

  const profile = {
    candidateName: candidateNameInput.value,
    targetRole: targetRoleInput.value,
    positionTag: session.positionTag,
    applicationType: applicationTypeInput.value,
    resumeFileName: session.resumeFileName,
    resume: resumeInput.value,
    jd: jdInput.value,
    company: companyInput.value,
    mode: modeInput.value,
    depth: depthInput.value,
    applicationProfileId: session.selectedProfileId,
  };

  session.currentIndex = 0;
  session.profile = profile;
  session.depth = depthInput.value;
  session.answers = [];
  session.usingModel = false;
  session.savedReportId = null;
  session.latestReport = null;

  sessionTitle.textContent = profile.targetRole || profile.mode;
  sourceBadge.textContent = "生成中";
  progressText.textContent = "生成中";
  emptyState.classList.add("hidden");
  interviewState.classList.remove("hidden");
  reportPanel.classList.add("hidden");
  setSaveStatus("尚未生成");

  try {
    const result = await requestJson("/api/interview/next-question", {
      profile,
      applicationProfileId: session.selectedProfileId,
      history: [],
      nextStage: getActiveStages()[0].stage,
      agentMode: agentModeInput?.value || "interview",
    }, { auth: true });
    session.questions = [
      normalizeQuestion(
        {
          stage: getActiveStages()[0].stage,
          stability: result.stability,
          focus: result.focus,
          prompt: result.prompt,
          agentDecision: result.agentDecision,
          decisionSummary: result.decisionSummary,
          ragReasons: result.ragReasons,
        },
        getActiveStages()[0]
      ),
    ];
    session.usingModel = true;
    sourceBadge.textContent = "真实模型";
  } catch (error) {
    console.warn("Using local question fallback:", error);
    session.questions = [buildFallbackQuestion(profile, 0)];
    sourceBadge.textContent = "本地兜底";
  }

  renderQuestion();
}

function saveCurrentAnswer() {
  const question = session.questions[session.currentIndex];
  const answer = answerInput.value.trim();
  session.answers[session.currentIndex] = {
    stage: question.stage,
    focus: question.focus,
    question: question.prompt,
    answer,
  };
  renderConversation();
}

function requireCurrentAnswer() {
  if (answerInput.value.trim()) {
    answerStatus.textContent = "";
    answerInput.dataset.status = "";
    return true;
  }
  answerStatus.textContent = "请先输入本题回答，再进入下一题。";
  answerInput.dataset.status = "empty";
  answerInput.focus();
  return false;
}

function estimateScore() {
  const answered = session.answers.filter((item) => item?.answer);
  const averageLength =
    answered.reduce((total, item) => total + item.answer.length, 0) / Math.max(answered.length, 1);
  const completeness = Math.round((answered.length / session.questions.length) * 40);
  const detail = Math.min(35, Math.round(averageLength / 8));
  const structure = answered.some((item) => /背景|负责|结果|因为|所以|首先|其次/.test(item.answer))
    ? 15
    : 8;

  return Math.min(95, Math.max(45, completeness + detail + structure));
}

function createList(items) {
  return `<ul>${items.map((item) => `<li>${item}</li>`).join("")}</ul>`;
}

function findAnswerForReview(review, index, answers = session.answers) {
  return answers[index] || answers.find((answer) => answer.question === review.question) || {};
}

function createQuestionReviewCards(questionReviews = [], answers = session.answers) {
  if (!Array.isArray(questionReviews) || questionReviews.length === 0) {
    return "";
  }

  const cards = questionReviews
    .map((review, index) => {
      const answer = findAnswerForReview(review, index, answers);
      const missingPoints = createList(review.missingPoints || []);
      return `
        <article class="question-review-card">
          <div class="question-review-heading">
            <div>
              <span class="eyebrow">第 ${review.index || index + 1} 题</span>
              <h3>${review.focus || answer.focus || "综合能力"}</h3>
            </div>
            <span class="status-badge">${review.answerStatus || "模糊"}</span>
          </div>
          <div class="review-detail">
            <strong>原问题</strong>
            <p>${review.question || answer.question || "本题未记录问题文本"}</p>
          </div>
          <div class="review-detail">
            <strong>我的回答</strong>
            <p>${answer.answer || "本题未作答"}</p>
          </div>
          <div class="review-detail">
            <strong>为什么问</strong>
            <p>${review.whyAsked || "用于确认当前考察点是否理解扎实。"}</p>
          </div>
          <div class="review-detail">
            <strong>缺失点</strong>
            ${missingPoints || "<p>建议补充概念解释、项目例子和验证方式。</p>"}
          </div>
          <div class="review-detail">
            <strong>参考回答方向</strong>
            <p>${review.referenceDirection || "建议按背景、做法、原因、结果的顺序组织回答。"}</p>
          </div>
          <div class="review-detail">
            <strong>下一步训练</strong>
            <p>${review.trainingAction || "围绕该考察点准备一段 1 分钟回答。"}</p>
          </div>
        </article>
      `;
    })
    .join("");

  return `
    <section class="question-review-section">
      <div class="section-heading compact">
        <span class="eyebrow">Learning Review</span>
        <h2>逐题学习复盘</h2>
      </div>
      <div class="question-review-list">${cards}</div>
    </section>
  `;
}

function createTrainingPlanSection(trainingPlan = {}) {
  const weakTopics = Array.isArray(trainingPlan.weakTopics) ? trainingPlan.weakTopics : [];
  const practiceQuestions = Array.isArray(trainingPlan.practiceQuestions) ? trainingPlan.practiceQuestions : [];
  const oneMinuteTemplates = Array.isArray(trainingPlan.oneMinuteTemplates) ? trainingPlan.oneMinuteTemplates : [];
  const nextRoundPriority = Array.isArray(trainingPlan.nextRoundPriority) ? trainingPlan.nextRoundPriority : [];

  if (
    weakTopics.length === 0 &&
    practiceQuestions.length === 0 &&
    oneMinuteTemplates.length === 0 &&
    nextRoundPriority.length === 0
  ) {
    return "";
  }

  const weakTopicCards = weakTopics
    .map(
      (topic) => `
        <article class="training-topic-card">
          <h3>${topic.focus || "综合能力"}</h3>
          <p>${topic.reason || "本轮回答暴露出该考察点仍需补强。"}</p>
          <strong>${topic.trainingAction || "准备一段 1 分钟回答。"}</strong>
        </article>
      `
    )
    .join("");

  return `
    <section class="training-plan-section">
      <div class="section-heading compact">
        <span class="eyebrow">Training Plan</span>
        <h2>下一轮训练计划</h2>
      </div>
      <div class="training-plan-grid">
        <article class="report-card">
          <h3>训练顺序</h3>
          ${createList(nextRoundPriority)}
          <p>${trainingPlan.shouldRetry ? "建议重练：先补薄弱点，再重新完成一轮模拟面试。" : "暂不强制重练：可以进入下一组岗位问题。"}</p>
        </article>
        <article class="report-card">
          <h3>推荐练习题</h3>
          ${createList(practiceQuestions)}
        </article>
        <article class="report-card">
          <h3>1 分钟回答模板</h3>
          ${createList(oneMinuteTemplates)}
        </article>
      </div>
      <div class="training-plan-actions">
        <button class="primary-button training-retry-button" type="button" data-retry-weak-topics="true">
          一键重练薄弱点
        </button>
        <p>自动切换为学习辅导模式，并把本轮薄弱点作为下一轮追问重点。</p>
      </div>
      ${weakTopicCards ? `<div class="training-topic-list">${weakTopicCards}</div>` : ""}
    </section>
  `;
}

function getPrimaryWeakFocus(trainingPlan = {}) {
  const weakTopics = Array.isArray(trainingPlan.weakTopics) ? trainingPlan.weakTopics : [];
  const nextRoundPriority = Array.isArray(trainingPlan.nextRoundPriority) ? trainingPlan.nextRoundPriority : [];
  return nextRoundPriority[0] || weakTopics[0]?.focus || "综合能力";
}

function inferRetryInterviewMode(focus = "") {
  if (/薪资|规划|行为|沟通|表达/.test(focus)) {
    return "HR 面";
  }
  if (/项目|简历|经历|职责|背景/.test(focus)) {
    return "项目深挖";
  }
  return "技术一面";
}

function buildWeakRetryContext(trainingPlan = {}) {
  const focus = getPrimaryWeakFocus(trainingPlan);
  const weakTopics = Array.isArray(trainingPlan.weakTopics) ? trainingPlan.weakTopics : [];
  const practiceQuestions = Array.isArray(trainingPlan.practiceQuestions) ? trainingPlan.practiceQuestions : [];
  const firstTopic = weakTopics.find((topic) => topic?.focus === focus) || weakTopics[0] || {};
  const parts = [
    `下一轮复练重点：${focus}`,
    firstTopic.reason ? `薄弱原因：${firstTopic.reason}` : "",
    firstTopic.trainingAction ? `训练动作：${firstTopic.trainingAction}` : "",
    practiceQuestions[0] ? `推荐练习题：${practiceQuestions[0]}` : "",
  ].filter(Boolean);
  return parts.join("\n");
}

function priorityLabel(priority) {
  return {
    high: "高优先级",
    medium: "中优先级",
    low: "低优先级",
  }[priority] || "中优先级";
}

function statusLabel(status) {
  return {
    todo: "待训练",
    in_progress: "训练中",
    done: "已完成",
    archived: "已归档",
  }[status] || "待训练";
}

function renderTrainingActionPlan(task = {}) {
  return `
    <div class="training-action-plan">
      <span>下一步训练</span>
      <strong>${task.title || "专项训练"}</strong>
      <p>${task.description || "围绕该薄弱点完成一次结构化回答练习。"}</p>
      <div class="training-plan-metrics">
        <span>掌握度：${task.masteryScore ?? 0}</span>
        <span>优先级：${priorityLabel(task.priority)}</span>
        <span>状态：${statusLabel(task.status)}</span>
      </div>
      ${
        task.recommendedQuestion
          ? `<div class="training-recommended-question">
              <small>推荐练习题</small>
              <p>${task.recommendedQuestion}</p>
            </div>`
          : ""
      }
    </div>
  `;
}

function selectedTrainingTask() {
  return (
    session.training.tasks.find((task) => task.id === session.training.selectedTaskId) ||
    session.training.tasks[0] ||
    null
  );
}

async function loadTrainingTasks() {
  if (!isLoggedIn()) {
    session.training.tasks = [];
    session.training.selectedTaskId = null;
    renderTrainingCenter();
    return;
  }

  try {
    const result = await requestGetJson("/api/training/tasks", { auth: true });
    session.training.tasks = Array.isArray(result.items) ? result.items : [];
    if (!session.training.tasks.some((task) => task.id === session.training.selectedTaskId)) {
      session.training.selectedTaskId = session.training.tasks[0]?.id || null;
    }
    renderTrainingCenter();
  } catch (error) {
    console.warn("Training tasks load failed:", error);
    if (trainingTaskList) {
      trainingTaskList.innerHTML = `<p class="empty-state">训练任务加载失败：${error.message}</p>`;
    }
  }
}

function renderTrainingCenter() {
  if (!trainingTaskList || !trainingTaskDetail) {
    return;
  }

  if (!isLoggedIn()) {
    trainingTaskList.innerHTML = `<p class="empty-state">登录后可以查看薄弱点训练任务。</p>`;
    trainingTaskDetail.innerHTML = "";
    return;
  }

  if (!session.training.tasks.length) {
    trainingTaskList.innerHTML = `<p class="empty-state">暂无训练任务，可以先完成一次面试复盘。</p>`;
    trainingTaskDetail.innerHTML = "";
    return;
  }

  trainingTaskList.innerHTML = session.training.tasks
    .map(
      (task) => `
        <button class="training-task-card ${task.id === session.training.selectedTaskId ? "active" : ""}" type="button" data-training-task-id="${task.id}">
          <strong>${task.title}</strong>
          <span>${task.weakLabel || task.weakTag}</span>
          <small>${priorityLabel(task.priority)} · 掌握度 ${task.masteryScore}</small>
        </button>
      `
    )
    .join("");

  const task = selectedTrainingTask();
  trainingTaskDetail.innerHTML = `
    <article class="training-detail-card">
      <p class="eyebrow">${task.weakTag}</p>
      <h3>${task.title}</h3>
      <p>${task.description || "围绕该薄弱点完成专项训练。"}</p>
      ${renderTrainingActionPlan(task)}
      <div class="training-meta-row">
        <span>状态：${statusLabel(task.status)}</span>
        <span>掌握度：${task.masteryScore}</span>
        <span>训练次数：${task.attemptCount}</span>
      </div>
      <div class="training-actions">
        <button class="primary-button" type="button" data-training-start="${task.id}">开始训练</button>
        <button class="secondary-button" type="button" data-training-complete="${task.id}">标记完成</button>
        <button class="ghost-button" type="button" data-training-archive="${task.id}">归档</button>
      </div>
    </article>
  `;
}

function replaceTrainingTask(updatedTask) {
  if (!updatedTask?.id) {
    return;
  }

  const taskIndex = session.training.tasks.findIndex((task) => task.id === updatedTask.id);
  if (taskIndex >= 0) {
    session.training.tasks[taskIndex] = { ...session.training.tasks[taskIndex], ...updatedTask };
  } else {
    session.training.tasks = [updatedTask, ...session.training.tasks];
  }
  session.training.selectedTaskId = updatedTask.id;
  renderTrainingCenter();
}

async function mutateTrainingTask(taskId, action, payload = {}) {
  if (!isLoggedIn()) {
    throw new Error("请先登录再操作训练任务");
  }

  const normalizedTaskId = Number(taskId);
  if (!normalizedTaskId) {
    throw new Error("训练任务 ID 无效");
  }

  const updatedTask = await requestJson(`/api/training/tasks/${normalizedTaskId}/${action}`, payload, { auth: true });
  replaceTrainingTask(updatedTask);
  return updatedTask;
}

async function startTrainingTask(taskId) {
  return mutateTrainingTask(taskId, "start");
}

async function completeTrainingTask(taskId, answerStatus = "完整") {
  return mutateTrainingTask(taskId, "complete", { answerStatus });
}

async function archiveTrainingTask(taskId) {
  return mutateTrainingTask(taskId, "archive");
}

function positiveIntegerOrNull(value) {
  const normalized = Number(value);
  return Number.isInteger(normalized) && normalized > 0 ? normalized : null;
}

async function generateTrainingTasksFromLatestReport() {
  if (!isLoggedIn() || !session.latestReport) {
    return;
  }

  await requestJson(
    "/api/training/tasks/generate-from-report",
    {
      applicationProfileId: positiveIntegerOrNull(session.selectedProfileId),
      sourceInterviewRecordId: positiveIntegerOrNull(session.savedReportId),
      report: session.latestReport,
    },
    { auth: true }
  );
  await loadTrainingTasks();
}

async function startWeakTopicRetry(trainingPlan = {}) {
  const retryContext = buildWeakRetryContext(trainingPlan);
  const focus = getPrimaryWeakFocus(trainingPlan);

  agentModeInput.value = "coach";
  depthInput.value = "quick";
  modeInput.value = inferRetryInterviewMode(focus);

  if (retryContext && !companyInput.value.includes(retryContext)) {
    companyInput.value = [companyInput.value.trim(), retryContext].filter(Boolean).join("\n");
  }

  setSaveStatus("正在开启薄弱点复练...");
  await generateTrainingTasksFromLatestReport().catch((error) => {
    console.warn("Training task generation failed:", error);
    setSaveStatus(`训练任务生成失败，仍继续复练：${error.message}`, true);
  });
  await startInterview({ preventDefault() {} });
}

function createAnswerReviewList(answers = []) {
  return `
    <div class="qa-list">
      ${answers
        .map(
          (answer, index) => `
            <article class="qa-item">
              <h3>${index + 1}. ${answer.focus || inferQuestionFocus(answer)}</h3>
              <p class="qa-question">${answer.question}</p>
              <p class="qa-answer">${answer.answer || "未作答"}</p>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function getHistory() {
  try {
    return normalizeHistory(JSON.parse(localStorage.getItem(historyStorageKey)) || []);
  } catch {
    return [];
  }
}

function normalizeHistory(history) {
  if (Array.isArray(history)) {
    return history;
  }
  if (Array.isArray(history?.items)) {
    return history.items;
  }
  return [];
}

function setLocalHistory(history) {
  localStorage.setItem(historyStorageKey, JSON.stringify(normalizeHistory(history).slice(0, 20)));
}

async function fetchServerHistory() {
  if (!isLoggedIn()) {
    return getHistory();
  }
  const response = await authFetch("/api/history");
  if (!response.ok) {
    throw new Error(`History request failed: ${response.status}`);
  }
  return response.json();
}

async function fetchServerStats() {
  if (!isLoggedIn()) {
    return renderStatsFallback(getHistory());
  }
  const response = await authFetch("/api/history/stats");
  if (!response.ok) {
    throw new Error(`History stats request failed: ${response.status}`);
  }
  return response.json();
}

async function saveServerHistory(report) {
  if (!isLoggedIn()) {
    throw new Error("请先登录再保存到数据库");
  }
  const response = await authFetch("/api/history", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      applicationProfileId: session.selectedProfileId,
      profile: session.profile,
      answers: session.answers.filter(Boolean),
      report,
    }),
  });

  if (!response.ok) {
    throw new Error(`History save failed: ${response.status}`);
  }

  return response.json();
}

function setSaveStatus(message, canRetry = false) {
  reportSaveStatus.textContent = message;
  retrySaveButton.classList.toggle("hidden", !canRetry);
}

async function saveHistoryItem(report, force = false) {
  session.latestReport = report;

  if (session.savedReportId && !force) {
    return;
  }

  try {
    setSaveStatus("正在保存到数据库...");
    const item = await saveServerHistory(report);
    session.savedReportId = item.id;
    setSaveStatus("已保存到数据库");
    await renderHistory();
    await renderUserCenter();
    return;
  } catch (error) {
    console.warn("Server history save failed, using localStorage:", error);
  }

  const history = getHistory();
  const item = {
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    profile: session.profile,
    applicationProfile: session.selectedProfileId
      ? applicationProfiles.find((profile) => profile.id === session.selectedProfileId) || null
      : null,
    answers: session.answers.filter(Boolean),
    report,
  };
  session.savedReportId = item.id;
  setLocalHistory([item, ...history]);
  setSaveStatus(isLoggedIn() ? "数据库保存失败，已本地暂存" : "未登录，已本地暂存", true);
  await renderHistory();
  await renderUserCenter();
}

function formatDate(value) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

async function loadHistory() {
  try {
    const serverHistory = normalizeHistory(await fetchServerHistory());
    if (isLoggedIn()) {
      setLocalHistory(serverHistory);
    }
    return serverHistory;
  } catch (error) {
    console.warn("Server history load failed, using localStorage:", error);
    return getHistory();
  }
}

function renderStatsFallback(history) {
  if (history.length === 0) {
    return {
      total: 0,
      averageScore: 0,
      bestScore: 0,
      latestScore: 0,
      latestRole: "",
      topRisks: [],
      topActions: [],
    };
  }

  const scores = history.map((item) => Number(item.report?.score) || 0);
  return {
    total: history.length,
    averageScore: Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length),
    bestScore: Math.max(...scores),
    latestScore: scores[0],
    latestRole: history[0]?.profile?.targetRole || "",
    topRisks: history.flatMap((item) => item.report?.risks || []).slice(0, 3),
    topActions: history.flatMap((item) => item.report?.actions || []).slice(0, 3),
  };
}

function readCurrentProfileForm() {
  const title = targetRoleInput.value.trim() || `${candidateNameInput.value.trim() || "我的"}投递档案`;
  return {
    title,
    targetRole: targetRoleInput.value,
    applicationType: applicationTypeInput.value,
    resume: resumeInput.value,
    jd: jdInput.value,
    company: companyInput.value,
    positionTag: session.positionTag,
  };
}

function applyApplicationProfile(profile) {
  targetRoleInput.value = profile.targetRole || "";
  applicationTypeInput.value = profile.applicationType || "实习投递";
  resumeInput.value = profile.resume || "";
  jdInput.value = profile.jd || "";
  companyInput.value = profile.company || "";
  session.positionTag = profile.positionTag || "";
  session.selectedProfileId = profile.id;
  profileStatus.innerHTML = `
    <article class="auth-protect-note">
      <strong>已选用档案：${profile.title}</strong>
      <p>左侧投递信息已回填，可以直接开始模拟面试，也可以继续微调简历和 JD。</p>
    </article>
  `;
}

async function fetchApplicationProfiles() {
  if (!isLoggedIn()) {
    applicationProfiles = [];
    return [];
  }
  const response = await authFetch("/api/application-profiles");
  if (!response.ok) {
    throw new Error(`Application profile request failed: ${response.status}`);
  }
  applicationProfiles = await response.json();
  return applicationProfiles;
}

async function saveCurrentApplicationProfile() {
  if (!isLoggedIn()) {
    profileStatus.innerHTML = `
      <article class="auth-protect-note">
        <strong>请先登录</strong>
        <p>投递档案需要保存到你的账号下，登录后才能跨设备查看和复用。</p>
      </article>
    `;
    return;
  }

  saveProfileButton.disabled = true;
  saveProfileButton.textContent = "保存中...";
  try {
    const response = await authFetch("/api/application-profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(readCurrentProfileForm()),
    });
    if (!response.ok) {
      throw await readResponseError(response);
    }
    await renderUserCenter();
  } catch (error) {
    console.warn("Application profile save failed:", error);
    profileStatus.innerHTML = `
      <article class="auth-protect-note">
        <strong>保存失败</strong>
        <p>${error.message}</p>
      </article>
    `;
  } finally {
    saveProfileButton.disabled = false;
    saveProfileButton.textContent = "保存当前档案";
  }
}

async function deleteApplicationProfile(profileId) {
  const response = await authFetch(`/api/application-profiles/${profileId}`, { method: "DELETE" });
  if (!response.ok) {
    throw await readResponseError(response);
  }
  await renderUserCenter();
}

async function renderUserCenter() {
  const localHistory = getHistory();
  let stats = renderStatsFallback(localHistory);
  try {
    stats = await fetchServerStats();
  } catch (error) {
    console.warn("User center stats load failed:", error);
  }

  if (!isLoggedIn()) {
    userCenterSummary.innerHTML = `
      <article class="auth-protect-note">
        <strong>登录后启用用户中心</strong>
        <p>这里会展示你的训练统计和投递档案。未登录时仍可临时练习，但数据主要保存在本机浏览器。</p>
      </article>
    `;
    profileStatus.innerHTML = "";
    profileList.innerHTML = "";
    saveProfileButton.disabled = true;
    return;
  }

  try {
    await fetchApplicationProfiles();
  } catch (error) {
    console.warn("Application profiles load failed:", error);
    profileList.innerHTML = `<p class="helper-text">投递档案加载失败：${error.message}</p>`;
  }

  saveProfileButton.disabled = false;
  profileStatus.innerHTML = "";
  userCenterSummary.innerHTML = `
    <article class="stat-card">
      <span>当前账号</span>
      <strong>${authState.user.username}</strong>
      <small>${authState.user.email}</small>
    </article>
    <article class="stat-card">
      <span>训练次数</span>
      <strong>${stats.total}</strong>
    </article>
    <article class="stat-card">
      <span>平均分</span>
      <strong>${stats.averageScore}</strong>
    </article>
    <article class="stat-card">
      <span>投递档案</span>
      <strong>${applicationProfiles.length}</strong>
    </article>
  `;

  if (!applicationProfiles.length) {
    profileList.innerHTML = `
      <div class="auth-protect-note">
        <strong>还没有投递档案</strong>
        <p>把左侧简历、JD、公司要求填好后，点击“保存当前档案”，以后就不用重复输入。</p>
      </div>
    `;
    return;
  }

  profileList.innerHTML = applicationProfiles
    .map(
      (profile) => `
        <article class="profile-item">
          <div>
            <h3>${profile.title}</h3>
            <p>${profile.targetRole || "未填写岗位"} · ${profile.applicationType || "未填写类型"}</p>
            <small>${profile.jd ? profile.jd.slice(0, 70) : "暂无 JD 摘要"}</small>
          </div>
          <div class="profile-actions">
            <button class="secondary-button" type="button" data-profile-use="${profile.id}">选用</button>
            <button class="secondary-button danger-button" type="button" data-profile-delete="${profile.id}">删除</button>
          </div>
        </article>
      `
    )
    .join("");
}

async function renderHistoryStats(history) {
  let stats = renderStatsFallback(history);
  try {
    stats = await fetchServerStats();
  } catch (error) {
    console.warn("Server stats load failed, using local stats:", error);
  }

  const riskList = stats.topRisks?.length ? createList(stats.topRisks) : "<p>完成面试后会生成风险点。</p>";
  const actionList = stats.topActions?.length ? createList(stats.topActions) : "<p>完成面试后会生成训练建议。</p>";

  historyStats.innerHTML = `
    <article class="stat-card">
      <span>训练次数</span>
      <strong>${stats.total}</strong>
    </article>
    <article class="stat-card">
      <span>平均分</span>
      <strong>${stats.averageScore}</strong>
    </article>
    <article class="stat-card">
      <span>最高分</span>
      <strong>${stats.bestScore}</strong>
    </article>
    <article class="stat-card">
      <span>最近一次</span>
      <strong>${stats.latestScore}</strong>
      <small>${stats.latestRole || "暂无岗位"}</small>
    </article>
    <article class="stat-card wide">
      <span>常见风险点</span>
      ${riskList}
    </article>
    <article class="stat-card wide">
      <span>高频训练建议</span>
      ${actionList}
    </article>
  `;
}

async function renderHistory() {
  const history = await loadHistory();
  currentHistory = Array.isArray(history) ? history : [];
  await renderHistoryStats(history);

  if (history.length === 0) {
    historyList.innerHTML = isLoggedIn()
      ? `<p class="helper-text">暂无云端历史记录。完成一次面试后会自动保存到当前账号。</p>`
      : `<div class="auth-protect-note">
          <strong>登录后查看云端复盘</strong>
          <p>未登录时报告会先暂存在本机浏览器；登录后可以保存到后端数据库，换设备也能继续查看。</p>
        </div>`;
    reviewPanel.classList.add("hidden");
    return;
  }

  historyList.innerHTML = currentHistory
    .map((item) => {
      const role = item.profile?.targetRole || item.profile?.mode || "模拟面试";
      const name = item.profile?.candidateName || "候选人";
      const score = Number(item.report?.score) || 0;
      const sourceProfile = item.applicationProfile?.title ? ` · 档案：${item.applicationProfile.title}` : "";
      return `
        <article class="history-item">
          <div>
            <h3>${role}</h3>
            <p>${name} · ${formatDate(item.createdAt)} · ${score} 分${sourceProfile}</p>
          </div>
          <button class="secondary-button" type="button" data-review-id="${item.id}">查看复盘</button>
        </article>
      `;
    })
    .join("");
}

function renderReview(item) {
  const report = item.report || {};
  const answers = Array.isArray(item.answers) ? item.answers : [];
  session.latestReport = report;
  session.profile = item.profile || session.profile;
  session.selectedProfileId = item.applicationProfileId || session.selectedProfileId;

  reviewPanel.innerHTML = `
    <header class="review-header">
      <div>
        <p class="eyebrow">Review</p>
        <h2>${item.profile?.targetRole || "模拟面试"} · ${Number(report.score) || 0} 分</h2>
        ${
          item.applicationProfile?.title
            ? `<p class="helper-text">来源档案：${item.applicationProfile.title}</p>`
            : ""
        }
      </div>
      <span>${formatDate(item.createdAt)}</span>
    </header>
    <div class="review-grid">
      <article class="report-card">
        <h3>主要优势</h3>
        ${createList(report.strengths || [])}
      </article>
      <article class="report-card">
        <h3>风险点</h3>
        ${createList(report.risks || [])}
      </article>
      <article class="report-card">
        <h3>下一步训练</h3>
        ${createList(report.actions || [])}
      </article>
    </div>
    ${createQuestionReviewCards(report.questionReviews || [], answers) || createAnswerReviewList(answers)}
    ${createTrainingPlanSection(report.trainingPlan || {})}
  `;
  reviewPanel.classList.remove("hidden");
  reviewPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderReport(result, note) {
  const strengths = Array.isArray(result.strengths) ? result.strengths : [];
  const risks = Array.isArray(result.risks) ? result.risks : [];
  const actions = Array.isArray(result.actions) ? result.actions : [];

  reportContent.innerHTML = `
    <article class="report-card">
      <h3>综合评分</h3>
      <div class="score">${Number(result.score) || 60}</div>
      <p>${note}</p>
    </article>
    <article class="report-card">
      <h3>主要优势</h3>
      ${createList(strengths)}
    </article>
    <article class="report-card">
      <h3>风险点</h3>
      ${createList(risks)}
    </article>
    <article class="report-card">
      <h3>下一步训练</h3>
      ${createList(actions)}
    </article>
    ${createTrainingPlanSection(result.trainingPlan || {})}
    ${createQuestionReviewCards(result.questionReviews || [], session.answers)}
  `;

  reportPanel.classList.remove("hidden");
  reportPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  saveHistoryItem({
    score: Number(result.score) || 60,
    strengths,
    risks,
    actions,
    questionReviews: result.questionReviews || [],
    trainingPlan: result.trainingPlan || {},
  });
}

function generateLocalReport() {
  saveCurrentAnswer();

  const score = estimateScore();
  const answered = session.answers.filter((item) => item?.answer);
  const missing = session.questions.length - answered.length;
  const hasProjectAnswer = answered.some((item) => item.stage === "项目深挖" && item.answer.length > 60);
  const hasTechAnswer = answered.some((item) => item.stage === "技术问答" && item.answer.length > 60);

  const strengths = [
    answered.length >= 4 ? "完成度较好，能跟完整轮面试流程。" : "已经开始建立面试表达习惯。",
    hasProjectAnswer ? "项目经历有一定展开，适合继续训练深挖追问。" : "简历经历可以作为后续重点训练材料。",
    "能围绕目标岗位进行准备，方向比随机刷题更清晰。",
  ];

  const risks = [
    missing > 0 ? `还有 ${missing} 个环节没有完整回答，真实面试中会影响稳定发挥。` : "下一步要提升回答的层次感和证据感。",
    hasTechAnswer ? "技术回答需要继续补充原理、场景和取舍。" : "技术问答部分需要更具体，避免只说概念。",
    "薪资和职业规划建议保持稳健，不要只表达个人期待，也要说明能给岗位带来的价值。",
  ];

  const actions = [
    "把自我介绍控制在 60 到 90 秒，并覆盖背景、技能、项目、求职目标。",
    "每个项目回答都按背景、任务、行动、结果来整理。",
    "技术题回答时补充使用场景、常见问题和你自己的实践。",
    "下一版可以接入真实模型 API，让面试官根据你的回答继续追问。",
  ];

  renderReport(
    {
      score,
      strengths,
      risks,
      actions,
    },
    "这是基于回答完整度、表达细节和结构化程度的 MVP 估算分。"
  );
}

async function generateReport() {
  saveCurrentAnswer();

  try {
    const result = await requestJson("/api/interview/report", {
      profile: session.profile,
      applicationProfileId: session.selectedProfileId,
      answers: session.answers,
    }, { auth: true });
    sourceBadge.textContent = "真实模型";
    renderReport(result, "这是由模型根据本轮回答生成的结构化反馈。");
  } catch (error) {
    console.warn("Using local report fallback:", error);
    sourceBadge.textContent = "本地兜底";
    generateLocalReport();
  }
}

async function loadNextQuestion() {
  const nextIndex = session.currentIndex + 1;
  const nextStage = getActiveStages()[nextIndex];

  if (!nextStage) {
    await generateReport();
    return;
  }

  sourceBadge.textContent = "生成中";
  progressText.textContent = "生成中";
  nextButton.disabled = true;
  reportButton.disabled = true;

  try {
    const result = await requestJson("/api/interview/next-question", {
      profile: session.profile,
      applicationProfileId: session.selectedProfileId,
      history: session.answers,
      nextStage: nextStage.stage,
      agentMode: agentModeInput?.value || "interview",
    }, { auth: true });

    const candidateQuestion = normalizeQuestion(
      {
        stage: nextStage.stage,
        stability: result.stability || nextStage.stability,
        focus: result.focus,
        prompt: result.prompt,
        agentDecision: result.agentDecision,
        decisionSummary: result.decisionSummary,
        ragReasons: result.ragReasons,
      },
      nextStage
    );
    session.questions[nextIndex] = shouldSwitchFocus(candidateQuestion, session.answers)
      ? attachAgentDecision(buildSwitchFocusQuestion(session.profile, nextIndex, candidateQuestion.focus), candidateQuestion)
      : isRepeatedPrompt(candidateQuestion.prompt, session.questions)
        ? attachAgentDecision(
            buildFocusedFallbackQuestion(session.profile, nextIndex, session.answers[session.currentIndex]),
            candidateQuestion
          )
        : candidateQuestion;
    sourceBadge.textContent = "真实模型";
  } catch (error) {
    console.warn("Using local next-question fallback:", error);
    session.questions[nextIndex] = buildFallbackQuestion(session.profile, nextIndex);
    sourceBadge.textContent = "本地兜底";
  } finally {
    nextButton.disabled = false;
    reportButton.disabled = false;
  }

  session.currentIndex = nextIndex;
  renderQuestion();
}

async function goNext() {
  if (!requireCurrentAnswer()) {
    return;
  }
  saveCurrentAnswer();

  if (session.currentIndex >= getActiveStages().length - 1) {
    await generateReport();
    return;
  }

  await loadNextQuestion();
}

function bindWeakTopicRetry(container) {
  container.addEventListener("click", (event) => {
    const button = event.target.closest("[data-retry-weak-topics]");
    if (!button) {
      return;
    }
    startWeakTopicRetry(session.latestReport?.trainingPlan || {}).catch((error) => {
      console.warn("Weak topic retry failed:", error);
      setSaveStatus(`薄弱点复练启动失败：${error.message}`, true);
    });
  });
}

setupForm.addEventListener("submit", startInterview);
authForm.addEventListener("submit", submitAuth);
loginTabButton.addEventListener("click", () => {
  authMode = "login";
  renderAuthState();
});
registerTabButton.addEventListener("click", () => {
  authMode = "register";
  renderAuthState();
});
logoutButton.addEventListener("click", logout);
parseResumeButton.addEventListener("click", parseResumeFile);
matchPositionButton.addEventListener("click", matchPositions);
positionAgentResult.addEventListener("click", (event) => {
  const button = event.target.closest("[data-position-tag]");
  if (!button) {
    return;
  }

  session.positionTag = button.dataset.positionTag;
  targetRoleInput.value = button.dataset.positionTitle;
  positionAgentResult.querySelectorAll(".agent-match").forEach((item) => item.classList.remove("selected"));
  button.closest(".agent-match")?.classList.add("selected");
});
nextButton.addEventListener("click", goNext);
reportButton.addEventListener("click", generateReport);
bindWeakTopicRetry(reportContent);
bindWeakTopicRetry(reviewPanel);
trainingRefreshButton?.addEventListener("click", async () => {
  try {
    await loadTrainingTasks();
  } catch (error) {
    console.warn("Training tasks refresh failed:", error);
  }
});
trainingTaskList?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-training-task-id]");
  if (!button) {
    return;
  }
  session.training.selectedTaskId = Number(button.dataset.trainingTaskId);
  renderTrainingCenter();
});
trainingTaskDetail?.addEventListener("click", async (event) => {
  const startButton = event.target.closest("[data-training-start]");
  const completeButton = event.target.closest("[data-training-complete]");
  const archiveButton = event.target.closest("[data-training-archive]");
  const taskId = Number(
    startButton?.dataset.trainingStart ||
      completeButton?.dataset.trainingComplete ||
      archiveButton?.dataset.trainingArchive ||
      0
  );

  if (!taskId) {
    return;
  }

  try {
    if (startButton) {
      await startTrainingTask(taskId);
    } else if (completeButton) {
      await completeTrainingTask(taskId);
    } else if (archiveButton) {
      await archiveTrainingTask(taskId);
    }
  } catch (error) {
    console.warn("Training task update failed:", error);
    trainingTaskDetail.innerHTML += `<p class="helper-text">训练任务更新失败：${error.message}</p>`;
  }
});
adminNavButton?.addEventListener("click", async () => {
  if (!isAdminUser()) {
    return;
  }
  switchProductSection("admin-dashboard");
  adminDashboardPanel?.classList.remove("hidden");
  await loadAdminDashboard().catch((error) => {
    console.warn("Admin dashboard load failed:", error);
    adminDashboardContent.innerHTML = `<p class="empty-state">后台加载失败：${error.message}</p>`;
  });
  adminDashboardPanel?.scrollIntoView({ behavior: "smooth", block: "start" });
});
adminRefreshButton?.addEventListener("click", async () => {
  await loadAdminDashboard().catch((error) => {
    console.warn("Admin dashboard refresh failed:", error);
    adminDashboardContent.innerHTML = `<p class="empty-state">后台刷新失败：${error.message}</p>`;
  });
});
historyList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-review-id]");
  if (!button) {
    return;
  }

  const item = currentHistory.find((historyItem) => String(historyItem.id) === button.dataset.reviewId);
  if (item) {
    renderReview(item);
  }
});
clearHistoryButton.addEventListener("click", async () => {
  if (isLoggedIn()) {
    await authFetch("/api/history", { method: "DELETE" }).catch((error) => {
      console.warn("Server history clear failed:", error);
    });
  }
  localStorage.removeItem(historyStorageKey);
  renderHistory();
});

retrySaveButton.addEventListener("click", () => {
  if (!session.latestReport) {
    setSaveStatus("没有可保存的报告");
    return;
  }
  session.savedReportId = null;
  saveHistoryItem(session.latestReport, true);
});

saveProfileButton.addEventListener("click", saveCurrentApplicationProfile);
profileList.addEventListener("click", async (event) => {
  const useButton = event.target.closest("[data-profile-use]");
  if (useButton) {
    const profile = applicationProfiles.find((item) => String(item.id) === useButton.dataset.profileUse);
    if (profile) {
      applyApplicationProfile(profile);
    }
    return;
  }

  const deleteButton = event.target.closest("[data-profile-delete]");
  if (!deleteButton) {
    return;
  }

  try {
    await deleteApplicationProfile(deleteButton.dataset.profileDelete);
  } catch (error) {
    console.warn("Application profile delete failed:", error);
    profileStatus.innerHTML = `
      <article class="auth-protect-note">
        <strong>删除失败</strong>
        <p>${error.message}</p>
      </article>
    `;
  }
});

ragDocumentForm.addEventListener("submit", submitRagDocument);
ragDocumentRefreshButton.addEventListener("click", () => {
  loadRagDocuments().catch((error) => {
    console.warn("RAG documents refresh failed:", error);
    ragDocumentStatus.textContent = `加载失败：${error.message}`;
  });
});
ragDocumentList.addEventListener("click", async (event) => {
  const viewButton = event.target.closest("[data-rag-document-view]");
  if (viewButton) {
    try {
      await loadRagDocumentDetail(viewButton.dataset.ragDocumentView);
    } catch (error) {
      console.warn("RAG document detail failed:", error);
      ragDocumentDetail.innerHTML = `<p class="helper-text">切片详情加载失败：${error.message}</p>`;
    }
    return;
  }

  const deleteButton = event.target.closest("[data-rag-document-delete]");
  if (!deleteButton) {
    return;
  }

  try {
    await deleteRagDocument(deleteButton.dataset.ragDocumentDelete);
    ragDocumentStatus.textContent = "知识库文档已删除";
  } catch (error) {
    console.warn("RAG document delete failed:", error);
    ragDocumentStatus.textContent = `删除失败：${error.message}`;
  }
});

function renderRagLogItem(item) {
  const hits = Array.isArray(item.hits) ? item.hits : [];
  const quality = item.quality || {};
  const formatMetadata = (metadata = {}) => {
    const entries = Object.entries(metadata).filter(([, value]) => value !== undefined && value !== null && value !== "");
    if (!entries.length) {
      return "metadata: 未记录";
    }
    return entries
      .slice(0, 6)
      .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join("/") : value}`)
      .join("；");
  };
  const hitList = hits.length
    ? hits
        .map(
          (hit) => {
            const matched = [...(hit.matchedTokens || []), ...(hit.matchedKeywords || [])];
            return `
              <li>
                <strong>${hit.title || "未命名命中"}</strong>
                <span>${hit.source || hit.metadata?.source || "seed"} · ${hit.score ?? "无分数"}</span>
                <small>命中词：${matched.length ? matched.join("、") : "未记录"}</small>
                <small>${formatMetadata(hit.metadata || {})}</small>
              </li>
            `;
          }
        )
        .join("")
    : "<li>无命中内容</li>";

  return `
    <article class="rag-log-item">
      <div class="rag-log-meta">
        <strong>${item.retrieverName}</strong>
        <span>${item.requestType}</span>
        <span>${item.retrievalMode}</span>
        <span>命中 ${item.hitCount} 条</span>
        <span class="quality-pill ${quality.level || "miss"}">${quality.label || "未评估"}</span>
        <span>${item.usedInPrompt ? "已进入 prompt" : "未进入 prompt"}</span>
      </div>
      <div class="rag-quality-summary">
        <span>最高分 ${quality.maxScore ?? 0}</span>
        <span>平均分 ${quality.averageScore ?? 0}</span>
        <span>数据库 ${quality.databaseHitCount ?? 0}</span>
        <span>种子兜底 ${quality.seedHitCount ?? 0}</span>
      </div>
      <details>
        <summary>查看 query 和命中摘要</summary>
        <p>${item.queryText || "无 query"}</p>
        <p>${quality.reason || "暂无质量说明"}</p>
        <ul>${hitList}</ul>
      </details>
    </article>
  `;
}

function agentActionLabel(action) {
  const labels = {
    deep_follow_up: "继续深挖",
    switch_topic: "切换话题",
    lower_difficulty: "降低难度",
    raise_difficulty: "提高难度",
    summarize_feedback: "阶段反馈",
    finish_interview: "结束面试",
  };
  return labels[action] || action || "未知动作";
}

function formatAgentSummaryObject(value) {
  if (!value || typeof value !== "object") {
    return "无";
  }
  const entries = Object.entries(value).filter(([, item]) => item !== undefined && item !== null && item !== "");
  if (!entries.length) {
    return "无";
  }
  return entries
    .slice(0, 4)
    .map(([key, item]) => `${key}: ${Array.isArray(item) ? item.join("/") : item}`)
    .join("；");
}

function renderAgentNodeTrace(decision = {}) {
  const nodeTrace = Array.isArray(decision.nodeTrace) ? decision.nodeTrace : [];
  if (!nodeTrace.length) {
    return `<p>节点链路：未记录</p>`;
  }
  const items = nodeTrace
    .map(
      (node) => `
        <li>
          <strong>${node.nodeName || "unknown_node"}</strong>
          <span>${node.fallbackUsed ? "兜底" : "正常"}</span>
          <small>输入：${formatAgentSummaryObject(node.inputSummary)}；输出：${formatAgentSummaryObject(node.outputSummary)}</small>
        </li>
      `
    )
    .join("");
  return `
    <p>节点链路：</p>
    <ul class="agent-trace-list">${items}</ul>
  `;
}

function renderAgentToolCalls(decision = {}) {
  const toolCalls = Array.isArray(decision.toolCalls) ? decision.toolCalls : [];
  if (!toolCalls.length) {
    return `<p>工具调用：未记录</p>`;
  }
  const items = toolCalls
    .map((tool) => {
      const output = tool.outputSummary || {};
      const hitCount = output.hitCount ?? 0;
      const scores = Array.isArray(output.topScores) && output.topScores.length ? `；分数 ${output.topScores.join("/")}` : "";
      return `
        <li>
          <strong>${tool.toolName || "unknown_tool"}</strong>
          <span>${tool.success === false ? "失败" : "成功"}</span>
          <small>命中 ${hitCount} 条${scores}；耗时 ${tool.elapsedMs ?? 0}ms${tool.error ? `；错误：${tool.error}` : ""}</small>
        </li>
      `;
    })
    .join("");
  return `
    <p>工具调用：</p>
    <ul class="agent-trace-list">${items}</ul>
  `;
}

function renderAgentLogItem(item) {
  const tools = Array.isArray(item.tools) ? item.tools : [];
  const state = item.state || {};
  const decision = item.decision || {};
  const debugSignals = Object.keys(getAgentDebugSignals(item)).length ? getAgentDebugSignals(item) : getAgentDebugSignals(decision);
  const guardrailApplied = Boolean(item.guardrailApplied ?? decision.guardrailApplied ?? debugSignals.guardrailApplied);
  const topicShift = Object.keys(getAgentTopicShift(item)).length ? getAgentTopicShift(item) : getAgentTopicShift(decision);
  const triggerRules =
    Array.isArray(debugSignals.triggerRules) && debugSignals.triggerRules.length
      ? debugSignals.triggerRules
      : Array.isArray(decision.triggerRules)
        ? decision.triggerRules
        : [];
  const topicShiftText = topicShift.from || topicShift.to ? `${topicShift.from || "未知"} -> ${topicShift.to || "未知"}` : "未发生";
  return `
    <article class="agent-log-item">
      <div class="agent-log-heading">
        <div>
          <span>${item.requestType || "next_question"}</span>
          <h3>${agentActionLabel(item.nextAction)}</h3>
        </div>
        <strong class="${item.fallbackUsed ? "fallback" : "model"}">${item.fallbackUsed ? "兜底决策" : "模型决策"}</strong>
      </div>
      <div class="agent-log-meta">
        <span>${item.nextAction || "unknown"}</span>
        <span>${item.stage || "未知阶段"}</span>
        <span>${item.difficulty || "medium"}</span>
        <span>${item.focus || "综合追问"}</span>
      </div>
      <p>${item.reason || "暂无决策原因。"}</p>
      <div class="agent-state-row">
        <span>轮次 ${state.roundCount ?? 0}</span>
        <span>回答状态 ${state.answerStatus || "未知"}</span>
        <span>${item.createdAt ? new Date(item.createdAt).toLocaleString("zh-CN") : "无时间"}</span>
      </div>
      <div class="agent-log-debug-summary">
        <strong>调试摘要</strong>
        <span>保护规则：${guardrailLabel(guardrailApplied)}</span>
        <span>连续弱回答：${debugSignals.weakAnswerStreak ?? 0}</span>
        <span>重复问题：${debugSignals.repeatedQuestionCount ?? 0}</span>
        <span>话题迁移：${topicShiftText}</span>
        <div class="agent-rule-list">${renderRuleTags(triggerRules)}</div>
      </div>
      <details>
        <summary>查看工具和状态摘要</summary>
        <p>工具：${tools.join("、") || "未记录"}</p>
        <p>Agent 模式：${agentModeLabel(decision.agentMode || state.agentMode || "interview")}</p>
        <p>触发规则：${triggerRules.join("、") || "未记录"}</p>
        <p>剩余轮次：${state.remainingRounds ?? "未知"}；上一阶段：${state.nextStage || item.stage || "未知"}</p>
        ${renderAgentNodeTrace(decision)}
        ${renderAgentToolCalls(decision)}
      </details>
    </article>
  `;
}

function knowledgeBaseLabel(value) {
  const labels = {
    role_knowledge: "岗位知识库",
    question_bank: "题库 RAG",
  };
  return labels[value] || value || "未知知识库";
}

function ragStatusLabel(value) {
  const labels = {
    enabled: "启用",
    disabled: "停用",
    archived: "归档",
  };
  return labels[value] || value || "未知状态";
}

function ragVisibilityLabel(value) {
  const labels = {
    private: "私有",
    public: "公开",
  };
  return labels[value] || value || "未知权限";
}

function renderMetadataPreview(metadata = {}) {
  const entries = Object.entries(metadata || {}).filter(([, value]) => value !== undefined && value !== null && value !== "");
  if (!entries.length) {
    return `<span class="rag-meta-chip muted">metadata 未记录</span>`;
  }
  return entries
    .slice(0, 4)
    .map(([key, value]) => `<span class="rag-meta-chip">${key}: ${Array.isArray(value) ? value.join("/") : value}</span>`)
    .join("");
}

function renderRagLifecycleBadges(documentItem = {}) {
  return `
    <div class="rag-lifecycle-row">
      <span>${ragStatusLabel(documentItem.status)}</span>
      <span>${ragVisibilityLabel(documentItem.visibility)}</span>
      <span>chunk ${documentItem.chunkCount ?? 0}</span>
      <span>重复 chunk ${documentItem.duplicateChunkCount ?? 0}</span>
    </div>
  `;
}

function parseMetadataInput() {
  const raw = ragDocumentMetadataInput.value.trim();
  if (!raw) {
    return {};
  }
  try {
    const metadata = JSON.parse(raw);
    if (!metadata || Array.isArray(metadata) || typeof metadata !== "object") {
      throw new Error("metadata must be an object");
    }
    return metadata;
  } catch (error) {
    throw new Error(`元数据 JSON 格式不正确：${error.message}`);
  }
}

function renderRagDocumentList() {
  if (!isLoggedIn()) {
    ragDocumentList.innerHTML = `
      <div class="auth-protect-note">
        <strong>登录后管理知识库</strong>
        <p>知识库文档按用户隔离，登录后才能创建、查看和删除自己的 RAG 文档。</p>
      </div>
    `;
    ragDocumentDetail.innerHTML = "";
    ragDocumentSubmitButton.disabled = true;
    return;
  }

  ragDocumentSubmitButton.disabled = false;
  if (!ragDocuments.length) {
    ragDocumentList.innerHTML = `
      <div class="auth-protect-note">
        <strong>还没有知识库文档</strong>
        <p>左侧录入内容后，系统会自动切片，后续 RAG 检索会优先使用这些数据库 chunk。</p>
      </div>
    `;
    return;
  }

  ragDocumentList.innerHTML = ragDocuments
    .map(
      (documentItem) => `
        <article class="rag-doc-item">
          <div>
            <h3>${documentItem.title}</h3>
            <p>${knowledgeBaseLabel(documentItem.knowledgeBase)} · ${documentItem.chunkCount || 0} 个切片</p>
            ${renderRagLifecycleBadges(documentItem)}
            <div class="rag-meta-chip-row">${renderMetadataPreview(documentItem.metadata || {})}</div>
          </div>
          <div class="profile-actions">
            <button class="secondary-button" type="button" data-rag-document-view="${documentItem.id}">查看切片</button>
            <button class="secondary-button danger-button" type="button" data-rag-document-delete="${documentItem.id}">删除</button>
          </div>
        </article>
      `
    )
    .join("");
}

async function loadRagDocuments() {
  if (!isLoggedIn()) {
    ragDocuments = [];
    renderRagDocumentList();
    ragDocumentStatus.textContent = "请先登录";
    return [];
  }

  ragDocumentStatus.textContent = "正在加载知识库...";
  const response = await authFetch("/api/rag/documents");
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error?.message || result.detail || `RAG documents failed: ${response.status}`);
  }

  ragDocuments = result.items || [];
  renderRagDocumentList();
  ragDocumentStatus.textContent = `已加载 ${ragDocuments.length} 份文档`;
  return ragDocuments;
}

async function loadRagDocumentDetail(documentId) {
  ragDocumentDetail.innerHTML = `<p class="helper-text">正在加载切片详情...</p>`;
  const response = await authFetch(`/api/rag/documents/${documentId}`);
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error?.message || result.detail || `RAG document detail failed: ${response.status}`);
  }

  const documentItem = result.document || {};
  const chunks = result.chunks || [];
  ragDocumentDetail.innerHTML = `
    <article class="rag-doc-detail-card">
      <header>
        <div>
          <span>${knowledgeBaseLabel(documentItem.knowledgeBase)}</span>
          <h3>${documentItem.title}</h3>
        </div>
        <strong>${chunks.length} chunks</strong>
      </header>
      ${renderRagLifecycleBadges(documentItem)}
      <div class="rag-meta-chip-row detail">${renderMetadataPreview(documentItem.metadata || {})}</div>
      ${
        chunks.length
          ? chunks
              .map(
                (chunk) => `
                  <div class="rag-chunk-item">
                    <strong>#${chunk.chunkIndex + 1}</strong>
                    <p>${chunk.content}</p>
                    <small>${(chunk.keywords || []).join("、") || "暂无关键词"}</small>
                  </div>
                `
              )
              .join("")
          : "<p class=\"helper-text\">暂无切片。</p>"
      }
    </article>
  `;
}

async function submitRagDocument(event) {
  event.preventDefault();
  if (!isLoggedIn()) {
    ragDocumentStatus.textContent = "请先登录后再保存知识库文档。";
    return;
  }

  ragDocumentSubmitButton.disabled = true;
  ragDocumentStatus.textContent = "正在保存知识库文档...";
  try {
    const response = await authFetch("/api/rag/documents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: ragDocumentTitleInput.value.trim(),
        knowledgeBase: ragKnowledgeBaseInput.value,
        sourceType: "manual",
        content: ragDocumentContentInput.value.trim(),
        metadata: parseMetadataInput(),
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error?.message || result.detail || `RAG document save failed: ${response.status}`);
    }

    ragDocumentStatus.textContent = `已保存：${result.title}，生成 ${result.chunkCount} 个切片`;
    ragDocumentForm.reset();
    await loadRagDocuments();
    await loadRagDocumentDetail(result.id);
  } catch (error) {
    console.warn("RAG document save failed:", error);
    ragDocumentStatus.textContent = `保存失败：${error.message}`;
  } finally {
    ragDocumentSubmitButton.disabled = !isLoggedIn();
  }
}

async function deleteRagDocument(documentId) {
  const response = await authFetch(`/api/rag/documents/${documentId}`, { method: "DELETE" });
  if (!response.ok) {
    throw await readResponseError(response);
  }
  ragDocumentDetail.innerHTML = "";
  await loadRagDocuments();
}

function renderQualityCard(title, quality = {}) {
  return `
    <article class="quality-card ${quality.level || "miss"}">
      <span>${title}</span>
      <strong>${quality.label || "未评估"}</strong>
      <p>命中 ${quality.hitCount ?? 0} 条 · 最高分 ${quality.maxScore ?? 0} · 平均分 ${quality.averageScore ?? 0}</p>
      <small>数据库 ${quality.databaseHitCount ?? 0} 条，种子兜底 ${quality.seedHitCount ?? 0} 条</small>
    </article>
  `;
}

function renderQualityOverview(quality = {}) {
  return `
    <section class="quality-overview">
      ${renderQualityCard("岗位知识库", quality.roleKnowledge)}
      ${renderQualityCard("题库 RAG", quality.questionBank)}
      ${renderQualityCard("候选人画像", quality.candidateMemory)}
    </section>
  `;
}

function renderRagExplanationPanel(explanations = {}) {
  const items = Object.values(explanations).filter(Boolean);
  if (!items.length) {
    return "";
  }

  return `
    <section class="rag-explanation-panel">
      <div class="section-heading compact">
        <div>
          <span>RAG Debug</span>
          <h3>RAG 命中解释</h3>
        </div>
      </div>
      <div class="rag-explanation-grid">
        ${items
          .map((item) => {
            const label = item.retrieverLabel || item.retrieverName || "RAG";
            const summary = item.developerSummary || `${label}命中 ${item.hitCount ?? 0} 条，质量为${item.qualityLabel || "未评估"}。`;
            const terms = (item.matchedTerms || []).filter(Boolean).join("、") || "未记录";
            const titles = (item.topTitles || []).filter(Boolean).slice(0, 2).join("；") || "暂无";
            return `
              <article class="rag-explanation-card ${item.qualityLevel || "miss"}">
                <strong>${label}</strong>
                <p>${summary}</p>
                <small>命中标题：${titles}</small>
                <small>命中词：${terms}</small>
              </article>
            `;
          })
          .join("")}
      </div>
    </section>
  `;
}

function renderRagHitDiagnostics(hit = {}) {
  const variantNames = Array.isArray(hit.queryVariants)
    ? hit.queryVariants.map((item) => item.name || item.query || "").filter(Boolean).join(" / ")
    : "";
  const matchedQueryVariant = hit.matchedQueryVariant || hit.queryVariant || "";
  const rerankParts = [];
  if (hit.rerankExplanation) {
    rerankParts.push(hit.rerankExplanation);
  }
  if (hit.rerankScore !== undefined && hit.rerankScore !== null) {
    rerankParts.push(`重排分 ${hit.rerankScore}`);
  }
  if (hit.rankChange !== undefined && hit.rankChange !== null) {
    rerankParts.push(`名次变化 ${hit.rankChange}`);
  }

  if (!variantNames && !matchedQueryVariant && !rerankParts.length) {
    return "";
  }

  return `
    <div class="rag-hit-diagnostics">
      ${variantNames ? `<p>多路 query：${variantNames}</p>` : ""}
      ${matchedQueryVariant ? `<p>命中 query：${matchedQueryVariant}</p>` : ""}
      ${rerankParts.length ? `<p>重排：${rerankParts.join("；")}</p>` : ""}
    </div>
  `;
}

async function loadRagLogs() {
  ragDebugContent.innerHTML = "";

  if (!isLoggedIn()) {
    ragLogContent.innerHTML = `
      <div class="auth-protect-note">
        <strong>登录后查看 RAG 命中日志</strong>
        <p>RAG 日志按用户隔离，未登录时不会展示历史召回记录。</p>
      </div>
    `;
    return;
  }

  ragLogContent.innerHTML = `<p class="helper-text">正在加载最近 RAG 命中日志...</p>`;

  try {
    const response = await authFetch("/api/rag/logs/recent?limit=9");
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error?.message || result.detail || `RAG logs failed: ${response.status}`);
    }

    const items = result.items || [];
    if (!items.length) {
      ragLogContent.innerHTML = `
        <div class="auth-protect-note">
          <strong>暂无 RAG 命中日志</strong>
          <p>生成一次问题或报告后，这里会显示三个 retriever 的召回记录。</p>
        </div>
      `;
      return;
    }

    ragLogContent.innerHTML = `
      <div class="rag-log-header">
        <strong>最近 ${items.length} 条 RAG 命中日志</strong>
        <span>用于判断召回是否命中、是否进入 prompt</span>
      </div>
      ${items.map(renderRagLogItem).join("")}
    `;
  } catch (error) {
    console.warn("RAG logs load failed:", error);
    ragLogContent.innerHTML = `<p class="helper-text">RAG 日志加载失败：${error.message}</p>`;
  }
}

async function loadAgentLogs() {
  if (!isLoggedIn()) {
    agentLogContent.innerHTML = `
      <div class="auth-protect-note">
        <strong>登录后查看 Agent 决策日志</strong>
        <p>Agent 决策日志按用户隔离，未登录时不会展示历史调度记录。</p>
      </div>
    `;
    return;
  }

  agentLogContent.innerHTML = `<p class="helper-text">正在加载最近 Agent 决策日志...</p>`;

  try {
    const response = await authFetch("/api/agent/logs/recent?limit=8");
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error?.message || result.detail || `Agent logs failed: ${response.status}`);
    }

    const items = result.items || [];
    if (!items.length) {
      agentLogContent.innerHTML = `
        <div class="auth-protect-note">
          <strong>暂无 Agent 决策日志</strong>
          <p>提交一次面试回答后，这里会显示 Agent 的下一步动作、决策原因和使用工具。</p>
        </div>
      `;
      return;
    }

    agentLogContent.innerHTML = `
      <div class="rag-log-header">
        <strong>最近 ${items.length} 条 Agent 决策日志</strong>
        <span>用于观察追问、降难度、换话题和兜底情况</span>
      </div>
      ${items.map(renderAgentLogItem).join("")}
    `;
  } catch (error) {
    console.warn("Agent logs load failed:", error);
    agentLogContent.innerHTML = `<p class="helper-text">Agent 决策日志加载失败：${error.message}</p>`;
  }
}

async function loadRagDebug() {
  ragLogContent.innerHTML = "";

  const params = new URLSearchParams({
    name: candidateNameInput.value,
    role: targetRoleInput.value,
    positionTag: session.positionTag,
    resume: resumeInput.value.slice(0, 500),
    jd: jdInput.value.slice(0, 500),
    stage: session.questions[session.currentIndex]?.stage || "技术追问",
  });
  if (session.selectedProfileId) {
    params.set("applicationProfileId", String(session.selectedProfileId));
  }

  ragDebugContent.innerHTML = `<p class="helper-text">正在检索 RAG 上下文...</p>`;

  try {
    const response = await authFetch(`/api/rag/debug?${params.toString()}`);
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || `RAG debug failed: ${response.status}`);
    }

    const roleItems = result.roleKnowledge || [];
    const questionItems = result.questionBank || [];
    const memoryItems = result.candidateMemory || [];
    const candidateProfile = result.candidateProfile || {};
    ragDebugContent.innerHTML = `
      ${renderQualityOverview(result.quality || {})}
      ${renderRagExplanationPanel(result.explanations || {})}
      <article class="debug-card">
        <h3>岗位知识库命中</h3>
        ${
          roleItems.length
            ? roleItems
                .map(
                  (item) => `
                    <div class="debug-item">
                      <strong>${item.title}</strong>
                      <p>命中分数：${item.score ?? "无"}；命中词：${[
                        ...(item.matchedKeywords || []),
                        ...(item.matchedTokens || []),
                      ].join("、") || "无"}</p>
                      <p>${item.content}</p>
                      ${renderRagHitDiagnostics(item)}
                      <p>追问方向：${(item.follow_up_questions || []).slice(0, 2).join("；") || "无"}</p>
                      <p>评分点：${(item.scoring_points || []).slice(0, 3).join("；") || "无"}</p>
                      <p>风险信号：${(item.risk_signals || []).slice(0, 2).join("；") || "无"}</p>
                    </div>
                  `
                )
                .join("")
            : "<p>暂无命中。可以补充岗位 JD 或知识库。</p>"
        }
      </article>
      <article class="debug-card">
        <h3>题库 RAG 命中</h3>
        ${
          questionItems.length
            ? questionItems
                .map(
                  (item) => `
                    <div class="debug-item">
                      <strong>${item.question}</strong>
                      <p>命中分数：${item.score ?? "无"}；岗位标签：${item.position_tag}</p>
                      <p>命中词：${[...(item.matchedTags || []), ...(item.matchedTokens || [])].join("、") || "无"}</p>
                      ${renderRagHitDiagnostics(item)}
                      <p>答题要点：${(item.key_points || []).join("；") || "无"}</p>
                    </div>
                  `
                )
                .join("")
            : "<p>暂无题库命中。可以补充岗位标签、JD 或题库数据。</p>"
        }
      </article>
      <article class="debug-card">
        <h3>候选人长期画像</h3>
        ${
          candidateProfile.hasHistory
            ? `
              <div class="debug-item">
                <strong>训练概况</strong>
                <p>平均分：${candidateProfile.averageScore ?? 0}；最近分数：${candidateProfile.latestScore ?? 0}；最高分：${candidateProfile.bestScore ?? 0}</p>
                <p>分数趋势：${(candidateProfile.scoreTrend || []).join(" → ") || "暂无"}</p>
                <p>薄弱环节：${(candidateProfile.weakStages || []).join("；") || "暂无"}</p>
                <p>高频风险：${(candidateProfile.frequentRisks || []).slice(0, 3).join("；") || "暂无"}</p>
                <p>训练重点：${(candidateProfile.trainingFocus || []).slice(0, 3).join("；") || "暂无"}</p>
              </div>
            `
            : "<p>暂无长期训练画像。完成几轮面试后这里会形成弱点和训练重点。</p>"
        }
      </article>
      <article class="debug-card">
        <h3>候选人历史命中</h3>
        ${
          memoryItems.length
            ? memoryItems
                .map(
                  (item) => `
                    <div class="debug-item">
                      <strong>${item.targetRole || "历史面试"}</strong>
                      <p>得分：${item.score}</p>
                      <p>风险点：${(item.risks || []).join("；") || "无"}</p>
                      <p>建议：${(item.actions || []).join("；") || "无"}</p>
                    </div>
                  `
                )
                .join("")
            : "<p>暂无历史画像。完成几轮面试后这里会更有内容。</p>"
        }
      </article>
    `;
  } catch (error) {
    console.warn("RAG debug failed:", error);
    ragDebugContent.innerHTML = `<p class="helper-text">检索失败：${error.message}</p>`;
  }
}

ragLogButton.addEventListener("click", loadRagLogs);
ragDebugButton.addEventListener("click", loadRagDebug);
agentLogButton.addEventListener("click", loadAgentLogs);

bindProductNavigation();
switchProductSection("interview-workbench");
loadAuthState();
renderAuthState();
syncCurrentUser().finally(() => {
  renderHistory();
  renderUserCenter();
  loadRagDocuments().catch((error) => {
    console.warn("Initial RAG documents load failed:", error);
    ragDocumentStatus.textContent = `知识库加载失败：${error.message}`;
  });
});
