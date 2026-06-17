<template>
  <AppLayout>
    <section v-if="isRestoringAuth" class="permission-panel">
      <p class="eyebrow">Admin Console</p>
      <h1>正在恢复登录状态</h1>
      <p>系统正在根据本地 token 拉取当前用户信息，恢复完成后会继续判断管理员权限。</p>
    </section>

    <section v-else-if="!auth.isAdmin" class="permission-panel">
      <p class="eyebrow">Admin Console</p>
      <h1>当前账号没有管理员权限</h1>
      <p>
        后台入口只对管理员开放。前端隐藏入口只是体验控制，真正的权限校验仍然由后端
        <code>/api/admin/*</code> 接口负责。
      </p>
    </section>

    <section v-else class="admin-page">
      <header class="page-header">
        <div>
          <p class="eyebrow">Admin Console</p>
          <h1>管理员后台</h1>
        </div>
        <p>观察账号、RAG 质量、Agent 决策日志和系统配置，让 AI 应用不再是黑箱。</p>
      </header>

      <p v-if="admin.error" class="error">{{ admin.error }}</p>
      <p v-if="admin.loading" class="muted">后台数据加载中...</p>

      <section v-if="admin.summary" class="section">
        <div class="section-title">
          <h2>平台概览</h2>
        </div>
        <div class="metrics-grid">
          <article class="metric">
            <span>用户数</span>
            <strong>{{ admin.summary.userCount }}</strong>
          </article>
          <article class="metric">
            <span>面试记录</span>
            <strong>{{ admin.summary.interviewRecordCount }}</strong>
          </article>
          <article class="metric">
            <span>RAG 文档</span>
            <strong>{{ admin.summary.ragDocumentCount }}</strong>
          </article>
          <article class="metric">
            <span>RAG 日志</span>
            <strong>{{ admin.summary.ragRetrievalLogCount }}</strong>
          </article>
          <article class="metric">
            <span>Agent 日志</span>
            <strong>{{ admin.summary.agentDecisionLogCount }}</strong>
          </article>
        </div>
      </section>

      <section class="section ai-debug-section">
        <div class="section-title">
          <h2>AI 调试控制台</h2>
          <span>{{ admin.aiDebugRecent.length }} 条链路</span>
        </div>
        <p class="section-help">
          把一次提问拆成 RAG 召回、Agent 决策、LangGraph 执行和诊断建议，方便定位 AI 为什么这样问。
        </p>
        <div class="ai-debug-layout">
          <div class="trace-list">
            <h3>最近 AI 请求</h3>
            <button
              v-for="trace in admin.aiDebugRecent"
              :key="trace.traceId"
              type="button"
              class="trace-card"
              :class="{ active: admin.selectedAiDebugTraceId === trace.traceId }"
              @click="admin.loadAiDebugDetail(trace.traceId)"
            >
              <span>{{ trace.nextActionLabel || normalizeAction(trace.nextAction) }}</span>
              <small>
                {{ trace.agentMode || "未知模式" }} · RAG 命中 {{ trace.totalRagHits }} ·
                {{ trace.fallbackUsed ? "兜底规则已启用" : "模型决策正常" }}
              </small>
            </button>
            <p v-if="admin.aiDebugRecent.length === 0" class="muted">暂无 AI 调试链路。</p>
          </div>

          <div class="trace-detail">
            <p v-if="admin.aiDebugLoading" class="muted">AI 调试详情加载中...</p>
            <p v-if="admin.aiDebugError" class="error">{{ admin.aiDebugError }}</p>
            <template v-if="admin.selectedAiDebugDetail">
              <div class="debug-grid">
                <article class="debug-panel">
                  <h3>RAG 召回链路</h3>
                  <p>总命中：{{ debugNumber(admin.selectedAiDebugDetail.rag, "totalHitCount") }}</p>
                  <div v-for="item in debugRagItems" :key="debugRagKey(item)" class="mini-row">
                    <strong>{{ debugText(item, "retrieverLabel", "未知知识库") }}</strong>
                    <span>命中 {{ debugText(item, "hitCount", "0") }} 条 · {{ debugText(item, "qualityLevel", "unknown") }}</span>
                  </div>
                </article>

                <article class="debug-panel">
                  <h3>Agent 决策链路</h3>
                  <p>动作：{{ debugText(admin.selectedAiDebugDetail.agent, "nextActionLabel", "未知动作") }}</p>
                  <p>原因：{{ debugText(admin.selectedAiDebugDetail.agent, "reason", "暂无原因") }}</p>
                  <span v-if="debugBoolean(admin.selectedAiDebugDetail.agent, 'fallbackUsed')" class="warning-pill">
                    兜底规则已启用
                  </span>
                </article>

                <article class="debug-panel">
                  <h3>LangGraph 执行链路</h3>
                  <p>{{ debugText(admin.selectedAiDebugDetail.langgraph, "explanation", "暂无 LangGraph 摘要") }}</p>
                  <p>Runtime：{{ debugText(admin.selectedAiDebugDetail.langgraph, "runtime", "未记录") }}</p>
                  <p>状态：{{ debugText(admin.selectedAiDebugDetail.langgraph, "status", "未记录") }}</p>
                  <p>当前节点：{{ debugText(admin.selectedAiDebugDetail.langgraph, "currentNode", "暂无") }}</p>
                  <p>threadId：{{ debugText(admin.selectedAiDebugDetail.langgraph, "threadId", "暂无") }}</p>
                  <p>节点数：{{ debugNumber(admin.selectedAiDebugDetail.langgraph, "nodeTraceCount") }}</p>
                  <p>
                    人工介入：{{
                      debugBoolean(admin.selectedAiDebugDetail.langgraph, "requiresHumanReview")
                        ? "需要人工介入"
                        : "无需人工介入"
                    }}
                  </p>
                  <p>恢复决策：{{ debugText(admin.selectedAiDebugDetail.langgraph, "resumeDecision", "暂无") }}</p>
                  <span v-if="debugInterruptReason" class="warning-pill">{{ debugInterruptReason }}</span>
                  <div class="debug-subsection">
                    <h4>Runtime 对比</h4>
                    <p>可见链路：{{ debugText(admin.selectedAiDebugDetail.langgraph, "visibleRuntime", "未记录") }}</p>
                    <p>Quality Gate：{{ runtimeQualityPassed ? "通过" : "未通过" }}</p>
                    <p>Fallback：{{ runtimeFallbackToClassic ? "已回退 classic" : "未触发" }}</p>
                    <ul v-if="runtimeComparisonReasons.length" class="debug-list">
                      <li v-for="reason in runtimeComparisonReasons" :key="reason">{{ reason }}</li>
                    </ul>
                  </div>
                  <div v-if="hasRuntimeAudit" class="debug-subsection">
                    <h4>Runtime 审计</h4>
                    <p>请求链路：{{ runtimeAuditText("requestedRuntime") }}</p>
                    <p>允许链路：{{ runtimeAuditText("allowedRuntime") }}</p>
                    <p>最终可见：{{ runtimeAuditText("visibleRuntime") }}</p>
                    <p>回退状态：{{ runtimeAuditFallbackUsed ? "已回退" : "未回退" }}</p>
                    <ul v-if="runtimeAuditReasons.length" class="debug-list">
                      <li v-for="reason in runtimeAuditReasons" :key="reason">{{ reason }}</li>
                    </ul>
                  </div>
                </article>

                <article class="debug-panel">
                  <h3>诊断建议</h3>
                  <div
                    v-for="diagnostic in admin.selectedAiDebugDetail.diagnostics"
                    :key="diagnostic.type + diagnostic.title"
                    class="mini-row"
                  >
                    <strong>{{ diagnostic.title }}</strong>
                    <span>{{ diagnostic.message }}</span>
                  </div>
                  <p v-if="admin.selectedAiDebugDetail.diagnostics.length === 0" class="muted">暂无诊断建议。</p>
                </article>
              </div>
              <details class="raw-debug">
                <summary>查看原始调试 JSON</summary>
                <pre>{{ JSON.stringify(admin.selectedAiDebugDetail, null, 2) }}</pre>
              </details>
            </template>
            <p v-else class="muted">请选择一条 AI 请求查看调试详情。</p>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="section-title">
          <h2>账号管理</h2>
          <span>{{ admin.filteredUsers.length }} 个结果</span>
        </div>
        <div class="filters">
          <input v-model="admin.userSearch" type="search" placeholder="搜索邮箱或用户名" />
          <select v-model="admin.roleFilter" aria-label="按角色筛选">
            <option value="all">全部角色</option>
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
          </select>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>邮箱</th>
                <th>用户名</th>
                <th>角色</th>
                <th>注册时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in paginatedUsers" :key="user.id">
                <td>{{ user.id }}</td>
                <td>{{ user.email }}</td>
                <td>{{ user.username }}</td>
                <td>
                  <span class="pill">{{ formatRole(user.role) }}</span>
                </td>
                <td>{{ formatDate(user.createdAt) }}</td>
              </tr>
              <tr v-if="admin.filteredUsers.length === 0">
                <td colspan="5" class="empty-cell">暂无匹配账号</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="admin.filteredUsers.length > 0" class="pagination-bar">
          <p>{{ userRangeLabel }}</p>
          <label>
            每页
            <select v-model.number="userPageSize" aria-label="每页显示账号数量">
              <option v-for="option in userPageSizeOptions" :key="option" :value="option">{{ option }} 条</option>
            </select>
          </label>
          <div class="pagination-actions">
            <button type="button" :disabled="userPage <= 1" aria-label="上一页账号" @click="goToPreviousUserPage">
              上一页
            </button>
            <span>第 {{ userPage }} / {{ userPageCount }} 页</span>
            <button
              type="button"
              :disabled="userPage >= userPageCount"
              aria-label="下一页账号"
              @click="goToNextUserPage"
            >
              下一页
            </button>
          </div>
        </div>
      </section>

      <section v-if="admin.ragQuality" class="section">
        <div class="section-title">
          <h2>RAG 质量诊断</h2>
          <span>最近 {{ admin.ragQuality.summary.totalLogCount }} 条日志</span>
        </div>
        <p class="section-help">
          用于判断 RAG 是不是找到了合适资料。如果这里异常，优先检查知识库内容、检索关键词、chunk 切分和 Prompt 拼接。
        </p>
        <div class="quality-grid">
          <article>
            <span>低质量召回</span>
            <strong>{{ admin.ragQuality.summary.lowQualityCount }}</strong>
            <small>需要人工关注的召回样例</small>
          </article>
          <article>
            <span>空召回</span>
            <strong>{{ admin.ragQuality.summary.emptyRecallCount }}</strong>
            <small>没有找到任何可用资料</small>
          </article>
          <article>
            <span>弱召回</span>
            <strong>{{ admin.ragQuality.summary.weakRecallCount }}</strong>
            <small>命中了资料，但相关性偏弱</small>
          </article>
          <article>
            <span>未进入 Prompt</span>
            <strong>{{ admin.ragQuality.summary.unusedInPromptCount }}</strong>
            <small>检索到了但未进入模型上下文</small>
          </article>
        </div>
        <div class="list">
          <article v-for="item in admin.ragQuality.items" :key="item.id || queryText(item)" class="log-item">
            <div class="log-heading">
              <strong>{{ queryText(item) }}</strong>
              <span class="warning-pill">{{ issueLabel(item.issueType) }}</span>
            </div>
            <p>检索器：{{ retrieverLabel(retrieverName(item)) }} · 命中 {{ hitCount(item) }} 条</p>
            <p class="advice-line">建议动作：{{ issueAdvice(item) }}</p>
          </article>
          <p v-if="admin.ragQuality.items.length === 0" class="muted">暂无低质量 RAG 召回样例。</p>
        </div>
      </section>

      <section class="section">
        <div class="section-title">
          <h2>RAG 文档概览</h2>
          <span>{{ admin.ragDocuments.length }} 份文档</span>
        </div>
        <p class="section-help">
          用于查看知识库资料是否已经入库、属于哪个知识库、是否启用，以及是否存在重复切片等维护风险。
        </p>
        <div class="list">
          <article v-for="document in admin.ragDocuments" :key="document.id" class="log-item">
            <strong>{{ document.title }}</strong>
            <p>
              {{ retrieverLabel(knowledgeBase(document)) }} · {{ documentStatusLabel(document.status) }} ·
              {{ documentVisibilityLabel(document.visibility) }}
            </p>
            <p>
              chunk {{ chunkCount(document) }}，重复 {{ duplicateChunkCount(document) }}，所属
              {{ document.userEmail || "未知用户" }}
            </p>
            <p v-if="documentRiskHint(document)" class="risk-line">{{ documentRiskHint(document) }}</p>
          </article>
          <p v-if="admin.ragDocuments.length === 0" class="muted">暂无 RAG 文档。</p>
        </div>
      </section>

      <section class="section">
        <div class="section-title">
          <h2>Agent 决策日志</h2>
          <span>{{ admin.agentLogs.length }} 条记录</span>
        </div>
        <p class="section-help">
          用于观察面试 Agent 为什么追问、降难度、换话题或结束。这里能帮助排查模型决策是否进入兜底规则。
        </p>
        <div class="list">
          <article v-for="log in admin.agentLogs" :key="log.id || log.createdAt || log.reason" class="log-item">
            <div class="log-heading">
              <strong>下一步动作：{{ normalizeAction(log.nextAction || log.next_action) }}</strong>
              <span v-if="isFallbackUsed(log)" class="warning-pill">{{ fallbackLabel(log) }}</span>
            </div>
            <p>当前阶段：{{ log.stage || "未知阶段" }} · 难度：{{ difficultyLabel(log.difficulty) }} · 关注点：{{ log.focus || "未知关注点" }}</p>
            <p>判断依据：{{ log.reason || "暂无原因" }}</p>
            <p class="advice-line">{{ actionExplanation(log.nextAction || log.next_action) }}</p>
          </article>
          <p v-if="admin.agentLogs.length === 0" class="muted">暂无 Agent 决策日志。</p>
        </div>
      </section>

      <section v-if="admin.config" class="section">
        <div class="section-title">
          <h2>系统配置</h2>
        </div>
        <div class="config-grid">
          <p>
            <span>LLM</span>
            <strong>{{ admin.config.modelName || "未配置" }}</strong>
          </p>
          <p>
            <span>Embedding</span>
            <strong>{{ admin.config.embeddingModel || "未配置" }}</strong>
          </p>
          <p>
            <span>Rerank</span>
            <strong>{{ admin.config.rerankModel || "未配置" }}</strong>
          </p>
          <p>
            <span>Database</span>
            <strong>{{ maskDatabaseUrl(admin.config.databaseUrl) }}</strong>
          </p>
        </div>
      </section>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import AppLayout from "@/layouts/AppLayout.vue";
import { useAdminStore } from "@/stores/admin";
import { useAuthStore } from "@/stores/auth";
import type { AdminAgentLog, AdminRagDocument, AdminRagQualityItem } from "@/api/admin";

type DebugRecord = Record<string, unknown>;

const auth = useAuthStore();
const admin = useAdminStore();
const isRestoringAuth = computed(() => auth.loading || (auth.isAuthenticated && !auth.user));
const userPageSizeOptions = [5, 10, 20];
const userPageSize = ref(10);
const userPage = ref(1);

const userPageCount = computed(() => Math.max(1, Math.ceil(admin.filteredUsers.length / userPageSize.value)));
const paginatedUsers = computed(() => {
  const start = (userPage.value - 1) * userPageSize.value;
  return admin.filteredUsers.slice(start, start + userPageSize.value);
});
const debugRagItems = computed(() => {
  const rag = admin.selectedAiDebugDetail?.rag as DebugRecord | undefined;
  return Array.isArray(rag?.items) ? (rag.items as DebugRecord[]) : [];
});
const debugInterruptReason = computed(() => {
  const langgraph = admin.selectedAiDebugDetail?.langgraph as DebugRecord | undefined;
  const interrupt = langgraph?.interrupt as DebugRecord | undefined;
  return typeof interrupt?.reason === "string" ? interrupt.reason : "";
});
const runtimeQualityPassed = computed(() => {
  const langgraph = admin.selectedAiDebugDetail?.langgraph as DebugRecord | undefined;
  const gate = langgraph?.qualityGate as DebugRecord | undefined;
  return Boolean(gate?.passed);
});
const runtimeFallbackToClassic = computed(() => {
  const langgraph = admin.selectedAiDebugDetail?.langgraph as DebugRecord | undefined;
  const gate = langgraph?.qualityGate as DebugRecord | undefined;
  const comparisonSummary = langgraph?.comparisonSummary as DebugRecord | undefined;
  const comparison = comparisonSummary?.comparison as DebugRecord | undefined;
  return Boolean(gate?.fallbackToClassic || comparison?.fallbackToClassic);
});
const runtimeComparisonReasons = computed(() => {
  const langgraph = admin.selectedAiDebugDetail?.langgraph as DebugRecord | undefined;
  const comparisonSummary = langgraph?.comparisonSummary as DebugRecord | undefined;
  const comparison = comparisonSummary?.comparison as DebugRecord | undefined;
  const reasons = comparison?.reasons;
  return Array.isArray(reasons) ? reasons.map(String).filter(Boolean) : [];
});
const runtimeAudit = computed(() => {
  const langgraph = admin.selectedAiDebugDetail?.langgraph as DebugRecord | undefined;
  const audit = langgraph?.runtimeAudit;
  return audit && typeof audit === "object" ? (audit as DebugRecord) : {};
});
const hasRuntimeAudit = computed(() => Object.keys(runtimeAudit.value).length > 0);
const runtimeAuditFallbackUsed = computed(() => Boolean(runtimeAudit.value.fallbackUsed));
const runtimeAuditReasons = computed(() => {
  const policyReasons = Array.isArray(runtimeAudit.value.policyReasons) ? runtimeAudit.value.policyReasons : [];
  const qualityGateReasons = Array.isArray(runtimeAudit.value.qualityGateReasons)
    ? runtimeAudit.value.qualityGateReasons
    : [];
  return [...policyReasons, ...qualityGateReasons].map(String).filter(Boolean);
});
const userRangeLabel = computed(() => {
  const total = admin.filteredUsers.length;
  if (total === 0) return "显示 0 条，共 0 条";
  const start = (userPage.value - 1) * userPageSize.value + 1;
  const end = Math.min(start + userPageSize.value - 1, total);
  return `显示 ${start}-${end} 条，共 ${total} 条`;
});

onMounted(() => {
  loadAdminDashboard();
});

watch(
  () => auth.isAdmin,
  () => {
    loadAdminDashboard();
  }
);

watch(
  () => [admin.userSearch, admin.roleFilter, userPageSize.value],
  () => {
    userPage.value = 1;
  }
);

watch(userPageCount, (pageCount) => {
  if (userPage.value > pageCount) {
    userPage.value = pageCount;
  }
});

async function loadAdminDashboard(): Promise<void> {
  if (auth.isAdmin && !admin.loading) {
    await admin.loadDashboard();
    const firstTrace = admin.aiDebugRecent[0];
    if (firstTrace && !admin.selectedAiDebugDetail) {
      void admin.loadAiDebugDetail(firstTrace.traceId);
    }
  }
}

function goToPreviousUserPage(): void {
  userPage.value = Math.max(1, userPage.value - 1);
}

function goToNextUserPage(): void {
  userPage.value = Math.min(userPageCount.value, userPage.value + 1);
}

function formatDate(value: string | null): string {
  if (!value) return "未知";
  return value.slice(0, 10);
}

function formatRole(role: string): string {
  if (role === "admin") return "管理员";
  if (role === "user") return "普通用户";
  return role || "未知";
}

function debugValue(source: unknown, key: string): unknown {
  if (!source || typeof source !== "object") return undefined;
  return (source as DebugRecord)[key];
}

function debugText(source: unknown, key: string, fallback = "暂无"): string {
  const value = debugValue(source, key);
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function debugNumber(source: unknown, key: string): number {
  const value = debugValue(source, key);
  const numberValue = Number(value ?? 0);
  return Number.isFinite(numberValue) ? numberValue : 0;
}

function debugBoolean(source: unknown, key: string): boolean {
  return Boolean(debugValue(source, key));
}

function runtimeAuditText(key: string): string {
  const value = runtimeAudit.value[key];
  if (value === null || value === undefined || value === "") return "未记录";
  return String(value);
}

function debugRagKey(item: DebugRecord): string {
  return `${debugText(item, "retrieverLabel")}-${debugText(item, "queryText")}-${debugText(item, "hitCount", "0")}`;
}

function queryText(item: AdminRagQualityItem): string {
  return item.queryText || item.query_text || "未知 query";
}

function retrieverName(item: AdminRagQualityItem): string {
  return item.retrieverName || item.retriever_name || "未知检索器";
}

function issueLabel(issueType = ""): string {
  const map: Record<string, string> = {
    empty_recall: "空召回：没有找到资料",
    weak_recall: "弱召回：找到了但相关性弱",
    unused_in_prompt: "未进入 Prompt：检索到了但没进入模型上下文",
    low_quality: "低质量召回：需要人工检查"
  };
  return map[issueType] || "未分类问题";
}

function issueAdvice(item: AdminRagQualityItem): string {
  const issueType = item.issueType || "";
  if (issueType === "empty_recall") return "补充岗位知识库或题库内容";
  if (issueType === "weak_recall") return "优化文档标题、metadata 或 chunk 内容";
  if (issueType === "unused_in_prompt") return "检查 Prompt 拼接逻辑或召回阈值";
  if (item.recommendation) return item.recommendation;
  return "查看原始命中日志，判断是否需要补充资料";
}

function retrieverLabel(value = ""): string {
  const map: Record<string, string> = {
    role_knowledge: "岗位知识库",
    question_bank: "题库",
    candidate_memory: "候选人画像",
    memory: "候选人画像"
  };
  return map[value] || value || "未知知识库";
}

function hitCount(item: AdminRagQualityItem): number {
  return item.hitCount ?? item.hit_count ?? 0;
}

function knowledgeBase(document: AdminRagDocument): string {
  return document.knowledgeBase || document.knowledge_base || "未知知识库";
}

function chunkCount(document: AdminRagDocument): number {
  return document.chunkCount ?? document.chunk_count ?? 0;
}

function duplicateChunkCount(document: AdminRagDocument): number {
  return document.duplicateChunkCount ?? document.duplicate_chunk_count ?? 0;
}

function documentStatusLabel(value = ""): string {
  const map: Record<string, string> = {
    enabled: "启用中",
    disabled: "已禁用",
    archived: "已归档"
  };
  return map[value] || value || "未知状态";
}

function documentVisibilityLabel(value = ""): string {
  const map: Record<string, string> = {
    public: "公共资料",
    private: "仅自己可用"
  };
  return map[value] || value || "未知可见性";
}

function documentRiskHint(document: AdminRagDocument): string {
  const duplicateCount = duplicateChunkCount(document);
  if (duplicateCount > 0) return `可能存在重复切片：${duplicateCount} 条，建议检查是否重复录入相同资料。`;
  return "";
}

function normalizeAction(action: AdminAgentLog["nextAction"] = ""): string {
  const map: Record<string, string> = {
    deep_follow_up: "继续深挖",
    deepen: "继续深挖",
    lower_difficulty: "降低难度",
    raise_difficulty: "提高难度",
    switch_topic: "切换话题",
    finish_interview: "结束面试",
    summarize_feedback: "总结反馈",
    practice_weakness: "专项训练"
  };
  return map[action] || action || "未知动作";
}

function difficultyLabel(value = ""): string {
  const map: Record<string, string> = {
    basic: "基础",
    medium: "中等",
    hard: "偏难"
  };
  return map[value] || value || "未知难度";
}

function actionExplanation(action = ""): string {
  const map: Record<string, string> = {
    deep_follow_up: "系统会围绕当前回答继续深挖，验证候选人是否真的理解。",
    deepen: "系统会围绕当前回答继续深挖，验证候选人是否真的理解。",
    lower_difficulty: "系统会降低问题难度，先帮助候选人补齐基础概念。",
    raise_difficulty: "系统会提高追问难度，验证候选人的实现细节和边界理解。",
    switch_topic: "系统会切换话题，避免一直卡在同一个知识点上。",
    finish_interview: "系统会结束本轮面试，并进入复盘报告生成。",
    summarize_feedback: "系统会先总结当前薄弱点，再给出更容易理解的反馈。",
    practice_weakness: "系统会转向专项训练，集中补候选人的薄弱点。"
  };
  return map[action] || "系统会根据当前状态继续生成下一轮问题。";
}

function isFallbackUsed(log: AdminAgentLog): boolean {
  return Boolean(log.fallbackUsed || log.fallback_used);
}

function fallbackLabel(log: AdminAgentLog): string {
  return isFallbackUsed(log) ? "兜底规则已启用" : "模型决策";
}

function maskDatabaseUrl(value: string): string {
  if (!value) return "未配置";
  if (value.includes("@")) return value.replace(/\/\/.*@/, "//***@");
  return value;
}
</script>

<style scoped>
.admin-page,
.permission-panel {
  display: grid;
  gap: 24px;
  max-width: 1180px;
  min-width: 0;
}

.page-header,
.section,
.permission-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  padding: 24px;
  min-width: 0;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.page-header > p {
  max-width: 520px;
  color: var(--color-text-muted);
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
}

h1,
h2,
p {
  margin: 0;
}

h1 {
  font-size: clamp(32px, 5vw, 48px);
  line-height: 1.05;
}

h2 {
  font-size: 20px;
}

code {
  border-radius: 6px;
  background: var(--color-surface-muted);
  padding: 2px 5px;
}

.permission-panel p,
.muted {
  color: var(--color-text-muted);
}

.error {
  border: 1px solid rgba(180, 35, 24, 0.22);
  border-radius: var(--radius-sm);
  background: #fff3f0;
  color: #b42318;
  padding: 12px 14px;
}

.section-title,
.filters,
.log-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-title span {
  color: var(--color-text-muted);
  font-size: 13px;
}

.metrics-grid,
.quality-grid,
.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.metric,
.quality-grid article,
.config-grid p,
.log-item {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-muted);
  padding: 14px;
}

.metric span,
.quality-grid span,
.config-grid span {
  display: block;
  margin-bottom: 6px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.section-help {
  margin-top: 10px;
  color: var(--color-text-muted);
  line-height: 1.7;
}

.metric strong,
.quality-grid strong {
  font-size: 26px;
  line-height: 1;
}

.quality-grid small {
  display: block;
  margin-top: 8px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.filters {
  margin: 16px 0;
}

.filters input,
.filters select {
  min-height: 42px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  padding: 10px 12px;
}

.filters input {
  min-width: min(360px, 100%);
}

.table-wrap {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
}

table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
}

th,
td {
  border-bottom: 1px solid var(--color-border);
  padding: 12px;
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
}

th {
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 600;
}

.empty-cell {
  color: var(--color-text-muted);
  text-align: center;
}

.pagination-bar,
.pagination-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pagination-bar {
  justify-content: space-between;
  margin-top: 14px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.pagination-bar label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.pagination-bar select,
.pagination-bar button {
  min-height: 36px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  padding: 7px 10px;
}

.pagination-bar button {
  cursor: pointer;
}

.pagination-bar button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.list {
  display: grid;
  gap: 10px;
  margin-top: 16px;
}

.ai-debug-layout {
  display: grid;
  grid-template-columns: minmax(220px, 300px) minmax(0, 1fr);
  gap: 16px;
  margin-top: 16px;
}

.trace-list,
.trace-detail,
.debug-panel {
  min-width: 0;
}

.trace-list h3,
.debug-panel h3 {
  margin: 0 0 10px;
  font-size: 15px;
}

.trace-card {
  display: grid;
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-muted);
  color: var(--color-text);
  cursor: pointer;
  gap: 6px;
  margin-bottom: 10px;
  padding: 12px;
  text-align: left;
}

.trace-card.active,
.trace-card:hover {
  border-color: rgba(23, 92, 211, 0.45);
  background: #f5f8ff;
}

.trace-card span {
  font-weight: 700;
}

.trace-card small,
.mini-row span {
  color: var(--color-text-muted);
  line-height: 1.5;
}

.debug-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.debug-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-muted);
  padding: 14px;
}

.debug-panel p {
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-bottom: 8px;
}

.debug-subsection {
  border-top: 1px solid var(--color-border);
  margin-top: 12px;
  padding-top: 12px;
}

.debug-subsection h4 {
  margin: 0 0 8px;
  font-size: 14px;
}

.debug-list {
  display: grid;
  gap: 6px;
  margin: 8px 0 0;
  padding-left: 18px;
}

.debug-list li {
  color: var(--color-text-muted);
  line-height: 1.5;
}

.mini-row {
  display: grid;
  gap: 4px;
  border-top: 1px solid var(--color-border);
  margin-top: 10px;
  padding-top: 10px;
  overflow-wrap: anywhere;
}

.raw-debug {
  margin-top: 12px;
}

.raw-debug summary {
  cursor: pointer;
  color: var(--color-text-muted);
}

.raw-debug pre {
  max-height: 320px;
  overflow: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #101828;
  color: #f2f4f7;
  padding: 12px;
  white-space: pre-wrap;
}

.log-item {
  display: grid;
  gap: 8px;
}

.log-item p {
  color: var(--color-text-muted);
  line-height: 1.6;
}

.advice-line {
  color: var(--color-text) !important;
}

.risk-line {
  border-left: 3px solid #f79009;
  padding-left: 10px;
}

.pill,
.warning-pill {
  display: inline-flex;
  border-radius: 999px;
  font-size: 12px;
  padding: 4px 8px;
  white-space: nowrap;
}

.pill {
  background: #eef4ff;
  color: #175cd3;
}

.warning-pill {
  background: #fff3cd;
  color: #7a4d00;
}

.config-grid strong {
  word-break: break-all;
}

@media (max-width: 760px) {
  .page-header,
  .section-title,
  .filters,
  .log-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .page-header,
  .section,
  .permission-panel {
    padding: 18px;
  }

  .filters input,
  .filters select {
    width: 100%;
  }

  .pagination-bar,
  .pagination-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .pagination-bar label,
  .pagination-bar select,
  .pagination-bar button {
    width: 100%;
  }

  .ai-debug-layout,
  .debug-grid {
    grid-template-columns: 1fr;
  }
}
</style>
