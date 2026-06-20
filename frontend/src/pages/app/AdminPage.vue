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
              <section v-if="workflowObservation" class="workflow-observation">
                <div class="section-title">
                  <h3>Agent 工作流观测</h3>
                  <span>{{ workflowObservation.runtime || "未记录 runtime" }}</span>
                </div>
                <div class="workflow-metrics">
                  <article>
                    <span>稳定兜底</span>
                    <strong>{{ workflowObservation.fallbackUsed ? "已触发" : "未触发" }}</strong>
                  </article>
                  <article>
                    <span>Quality Gate</span>
                    <strong>{{ workflowQualityGatePassed ? "通过" : "未通过" }}</strong>
                  </article>
                  <article>
                    <span>Checkpoint</span>
                    <strong>{{ workflowCheckpoint.exists ? "已保存" : "未保存" }}</strong>
                  </article>
                </div>
                <p class="section-help">
                  threadId：{{ workflowCheckpoint.threadId || "暂无" }} · 当前节点：{{
                    workflowCheckpoint.currentNode || "暂无"
                  }}
                </p>
                <div class="workflow-node-list">
                  <span v-for="node in workflowNodes" :key="node.nodeName || node.node">
                    {{ node.nodeName || node.node }}
                  </span>
                </div>
                <div class="workflow-rag-list">
                  <span v-for="item in workflowRagSummary" :key="item.retrieverLabel">
                    {{ item.retrieverLabel }} · 命中 {{ item.hitCount }} · {{ item.qualityLevel }}
                  </span>
                </div>
              </section>
              <nav class="debug-tabs" aria-label="AI 调试详情分区">
                <button
                  v-for="tab in aiDebugTabs"
                  :key="tab.key"
                  type="button"
                  :data-testid="`ai-debug-tab-${tab.key}`"
                  :aria-selected="admin.selectedAiDebugTab === tab.key"
                  @click="admin.setAiDebugTab(tab.key)"
                >
                  {{ tab.label }}
                </button>
              </nav>
              <div class="debug-grid">
                <article v-if="admin.selectedAiDebugTab === 'overview'" class="debug-panel">
                  <h3>一句话诊断</h3>
                  <p>{{ aiDebugOverviewText }}</p>
                  <div class="quality-grid compact">
                    <article>
                      <span>请求类型</span>
                      <strong>{{ debugText(admin.selectedAiDebugDetail.summary, "requestType", "未知") }}</strong>
                    </article>
                    <article>
                      <span>RAG 总命中</span>
                      <strong>{{ debugNumber(admin.selectedAiDebugDetail.rag, "totalHitCount") }}</strong>
                    </article>
                    <article>
                      <span>主要动作</span>
                      <strong>{{ debugText(admin.selectedAiDebugDetail.agent, "nextActionLabel", "未知") }}</strong>
                    </article>
                    <article>
                      <span>Fallback</span>
                      <strong>{{ debugBoolean(admin.selectedAiDebugDetail.agent, "fallbackUsed") ? "已触发" : "未触发" }}</strong>
                    </article>
                  </div>
                </article>

                <article v-else-if="admin.selectedAiDebugTab === 'rag'" class="debug-panel">
                  <h3>RAG 召回链路</h3>
                  <p>总命中：{{ debugNumber(admin.selectedAiDebugDetail.rag, "totalHitCount") }}</p>
                  <div v-for="item in debugRagSummary" :key="debugRagSummaryKey(item)" class="mini-row">
                    <strong>{{ item.label || item.knowledgeBase || "未知知识库" }}</strong>
                    <span>
                      命中 {{ item.hitCount }} 条 · {{ item.qualityLabel || qualityLevelLabel(item.quality) }}
                      <template v-if="item.occurrenceCount > 1"> · 出现 {{ item.occurrenceCount }} 次</template>
                    </span>
                  </div>
                  <div v-for="item in debugRagRawItems" :key="debugRagKey(item)" class="mini-row">
                    <strong>{{ debugText(item, "retrieverLabel", "未知知识库") }}</strong>
                    <span>
                      命中 {{ debugText(item, "hitCount", "0") }} 条 ·
                      {{ qualityLevelLabel(debugText(item, "qualityLevel", "unknown")) }}
                    </span>
                  </div>
                </article>

                <article v-else-if="admin.selectedAiDebugTab === 'agent'" class="debug-panel">
                  <h3>Agent 决策链路</h3>
                  <p>动作：{{ debugText(admin.selectedAiDebugDetail.agent, "nextActionLabel", "未知动作") }}</p>
                  <p>原因：{{ debugText(admin.selectedAiDebugDetail.agent, "reason", "暂无原因") }}</p>
                  <span v-if="debugBoolean(admin.selectedAiDebugDetail.agent, 'fallbackUsed')" class="warning-pill">
                    兜底规则已启用
                  </span>
                </article>

                <article v-else-if="admin.selectedAiDebugTab === 'langgraph'" class="debug-panel">
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
                  <div v-if="hasReplaySummary" class="debug-subsection">
                    <h4>运行时间线</h4>
                    <p>{{ replaySummaryText }}</p>
                    <div v-for="step in replayTimeline" :key="`${step.step}-${step.node}`" class="mini-row">
                      <strong>{{ step.step }}. {{ step.title }}</strong>
                      <span>{{ step.node }} · {{ step.detail }}</span>
                    </div>
                    <div v-if="replayRisks.length" class="debug-subsection compact">
                      <h4>风险标记</h4>
                      <ul class="debug-list">
                        <li v-for="risk in replayRisks" :key="risk">{{ risk }}</li>
                      </ul>
                    </div>
                    <div v-if="replayNextActions.length" class="debug-subsection compact">
                      <h4>建议动作</h4>
                      <ul class="debug-list">
                        <li v-for="action in replayNextActions" :key="action">{{ reviewActionLabel(action) }}</li>
                      </ul>
                    </div>
                  </div>
                  <div v-if="hasRuntimeReport" class="debug-subsection">
                    <h4>Runtime 报告</h4>
                    <p>{{ runtimeReportSummary }}</p>
                    <p>
                      运行 {{ runtimeReportNumber("totalRuns") }} 次 · fallback
                      {{ runtimeReportNumber("fallbackCount") }} 次 · 人审
                      {{ runtimeReportNumber("humanReviewCount") }} 次
                    </p>
                    <ul v-if="runtimeReportReasons.length" class="debug-list">
                      <li v-for="item in runtimeReportReasons" :key="item.reason">
                        {{ item.reason }}：{{ item.count }} 次
                      </li>
                    </ul>
                  </div>
                </article>

                <article v-else-if="admin.selectedAiDebugTab === 'diagnostics'" class="debug-panel">
                  <h3>诊断建议</h3>
                  <div
                    v-for="diagnostic in debugDiagnosticSummary"
                    :key="diagnostic.type + diagnostic.title"
                    class="mini-row"
                  >
                    <strong>{{ diagnostic.title }}</strong>
                    <span>
                      {{ diagnostic.message }}
                      <template v-if="diagnostic.count > 1"> · 出现 {{ diagnostic.count }} 次</template>
                    </span>
                  </div>
                  <p v-if="debugDiagnosticSummary.length === 0" class="muted">暂无诊断建议。</p>
                </article>

                <article v-else-if="admin.selectedAiDebugTab === 'raw'" class="debug-panel raw-debug">
                  <h3>原始调试日志</h3>
                  <details open>
                    <summary>查看原始调试 JSON</summary>
                    <pre>{{ JSON.stringify(admin.selectedAiDebugDetail, null, 2) }}</pre>
                  </details>
                </article>
              </div>
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
        <p v-if="admin.forceLogoutMessage" class="success-message">{{ admin.forceLogoutMessage }}</p>
        <p v-if="admin.forceLogoutError" class="error">{{ admin.forceLogoutError }}</p>
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
                <th>操作</th>
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
                <td>
                  <button
                    v-if="user.id !== auth.user?.id"
                    type="button"
                    class="table-action"
                    :data-testid="`force-logout-user-${user.id}`"
                    :disabled="admin.forceLogoutPendingUserId === user.id"
                    @click="openForceLogout(user)"
                  >
                    {{ admin.forceLogoutPendingUserId === user.id ? "下线中..." : "强制下线" }}
                  </button>
                </td>
              </tr>
              <tr v-if="admin.filteredUsers.length === 0">
                <td colspan="6" class="empty-cell">暂无匹配账号</td>
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

      <div v-if="forceLogoutCandidate" class="modal-backdrop" role="dialog" aria-modal="true">
        <section class="confirm-modal">
          <h2>确认强制下线该用户？</h2>
          <p>用户：{{ forceLogoutCandidate.email }}</p>
          <p>操作后，该用户当前登录态会失效，需要重新登录。</p>
          <div class="modal-actions">
            <button type="button" class="ghost-action" @click="closeForceLogout">取消</button>
            <button data-testid="confirm-force-logout" type="button" @click="confirmForceLogout">确认下线</button>
          </div>
        </section>
      </div>

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
            <span>高相关</span>
            <strong>{{ admin.ragQuality.summary.goodCount || Math.max(admin.ragQuality.summary.totalLogCount - admin.ragQuality.summary.lowQualityCount, 0) }}</strong>
            <small>可直接支撑面试追问的召回</small>
          </article>
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
        <div class="dashboard-panel">
          <h3>知识库质量分布</h3>
          <div v-for="item in admin.ragQuality.knowledgeBaseSummary || []" :key="item.knowledgeBase" class="mini-row">
            <strong>{{ item.label || retrieverLabel(item.knowledgeBase) }}</strong>
            <span>高相关 {{ item.goodCount }} / 弱相关 {{ item.weakCount }} / 空召回 {{ item.emptyCount }}</span>
          </div>
          <p v-if="!(admin.ragQuality.knowledgeBaseSummary || []).length" class="muted">暂无知识库质量分布。</p>
        </div>
        <div class="dashboard-panel">
          <h3>主要诊断</h3>
          <div v-for="item in admin.ragQuality.diagnosticSummary || []" :key="`${item.type}-${item.title}`" class="mini-row">
            <strong>{{ item.title }}</strong>
            <span>{{ item.message }} · 出现 {{ item.count }} 次</span>
          </div>
          <p v-if="!(admin.ragQuality.diagnosticSummary || []).length" class="muted">暂无主要诊断。</p>
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

      <section v-if="admin.ragIngestionTasks" class="section">
        <div class="section-title">
          <h2>RAG 摄取任务监控</h2>
          <span>{{ admin.ragIngestionTasks.summary.totalCount }} 个任务</span>
        </div>
        <p class="section-help">
          用于观察文档有没有成功进入知识库。若这里频繁失败，应先排查文件类型、文本解析、metadata 和入库逻辑。
        </p>
        <div class="quality-grid">
          <article>
            <span>处理中</span>
            <strong>{{ admin.ragIngestionTasks.summary.runningCount }}</strong>
            <small>正在解析或入库的任务</small>
          </article>
          <article>
            <span>已完成</span>
            <strong>{{ admin.ragIngestionTasks.summary.succeededCount }}</strong>
            <small>已经生成 RAG 文档</small>
          </article>
          <article>
            <span>失败任务</span>
            <strong>{{ admin.ragIngestionTasks.summary.failedCount }}</strong>
            <small>需要查看失败原因</small>
          </article>
          <article>
            <span>可重试</span>
            <strong>{{ admin.ragIngestionTasks.summary.retryableCount }}</strong>
            <small>已有文本快照，可重新入库</small>
          </article>
          <article>
            <span>最长耗时</span>
            <strong>{{ ingestionMaxDurationMs }}ms</strong>
            <small>最近任务中耗时最高的一次</small>
          </article>
          <article>
            <span>幂等命中</span>
            <strong>{{ ingestionIdempotencyHitCount }}</strong>
            <small>重复上传时复用已有任务的次数</small>
          </article>
        </div>
        <div v-if="ingestionFailureStageItems.length" class="failure-stage-list">
          <span v-for="item in ingestionFailureStageItems" :key="item.stage">
            {{ item.stage }} · {{ item.count }}
          </span>
        </div>
        <div class="list">
          <article v-for="task in admin.ragIngestionTasks.items" :key="task.taskId" class="log-item">
            <div class="log-heading">
              <strong>{{ task.title || task.originalFilename || task.taskId }}</strong>
              <span class="warning-pill">{{ ingestionStatusLabel(task.status) }}</span>
            </div>
            <p>
              {{ retrieverLabel(task.knowledgeBase) }} · 文件 {{ task.originalFilename || "未知文件" }} · 用户
              {{ task.userEmail || "未知用户" }}
            </p>
            <p>
              重试 {{ task.retryCount || 0 }}/{{ task.maxRetries || 0 }} ·
              {{ task.canRetry ? "可重试" : "不可重试" }}
            </p>
            <p v-if="task.error" class="risk-line">{{ task.error }}</p>
          </article>
          <p v-if="admin.ragIngestionTasks.items.length === 0" class="muted">暂无 RAG 摄取任务。</p>
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
        <div class="quality-grid">
          <article>
            <span>Ready 文档</span>
            <strong>{{ admin.ragDocumentDashboard.readyDocumentCount }}</strong>
            <small>当前启用中的资料数</small>
          </article>
          <article>
            <span>Ready chunk</span>
            <strong>{{ admin.ragDocumentDashboard.readyChunkCount }}</strong>
            <small>可被检索使用的切片数</small>
          </article>
          <article>
            <span>Embedding</span>
            <strong>{{ admin.config?.embeddingModel || "未配置" }}</strong>
            <small>当前向量模型</small>
          </article>
        </div>
        <div class="dashboard-panel">
          <h3>RAG 文档覆盖</h3>
          <div v-for="item in admin.ragDocumentDashboard.knowledgeBaseCoverage" :key="item.knowledgeBase" class="mini-row">
            <strong>{{ retrieverLabel(item.knowledgeBase) }}</strong>
            <span>Ready 文档 {{ item.readyDocumentCount }} / Ready chunk {{ item.readyChunkCount }}</span>
          </div>
          <p v-if="admin.ragDocumentDashboard.knowledgeBaseCoverage.length === 0" class="muted">暂无 RAG 文档覆盖数据。</p>
        </div>
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
        <div class="quality-grid">
          <article>
            <span>总决策</span>
            <strong>{{ admin.agentDashboardSummary.totalCount }}</strong>
            <small>最近记录的 Agent 决策数</small>
          </article>
          <article>
            <span>fallback</span>
            <strong>{{ admin.agentDashboardSummary.fallbackCount }}</strong>
            <small>fallback {{ admin.agentDashboardSummary.fallbackCount }} 次</small>
          </article>
        </div>
        <div class="dashboard-panel">
          <h3>Agent 动作分布</h3>
          <div v-for="item in admin.agentDashboardSummary.actionSummary" :key="item.action" class="mini-row">
            <strong>{{ normalizeAction(item.action) }}</strong>
            <span>{{ item.count }} 次</span>
          </div>
          <p v-if="admin.agentDashboardSummary.actionSummary.length === 0" class="muted">暂无 Agent 动作分布。</p>
        </div>
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
        <div v-if="admin.config.infrastructure" class="infra-panel">
          <h3>基础设施状态</h3>
          <div class="config-grid">
            <p>
              <span>Database</span>
              <strong>{{ databaseInfraLabel }}</strong>
              <small>{{ databaseMigrationLabel }}</small>
            </p>
            <p>
              <span>Redis</span>
              <strong>{{ redisInfraLabel }}</strong>
              <small>{{ redisInfraDetail }}</small>
            </p>
            <p>
              <span>Celery</span>
              <strong>{{ celeryInfraLabel }}</strong>
              <small>{{ celeryInfraDetail }}</small>
              <small v-if="celeryInfraModeLabel">{{ celeryInfraModeLabel }}</small>
              <small v-if="celeryWorkerCommandLabel">{{ celeryWorkerCommandLabel }}</small>
            </p>
            <p v-if="celeryWorkerReadinessLabel">
              <span>异步任务 Worker</span>
              <strong>{{ celeryWorkerReadinessStatusLabel }}</strong>
              <small>{{ celeryWorkerReadinessLabel }}</small>
            </p>
          </div>
        </div>
        <div v-if="admin.config.security" class="infra-panel">
          <h3>安全与流量保护</h3>
          <div class="config-grid">
            <p>
              <span>Token blacklist</span>
              <strong>{{ securityFeatureLabel("tokenBlacklist") }}</strong>
              <small>退出登录后 access token 可被撤销</small>
            </p>
            <p>
              <span>限流</span>
              <strong>{{ securityFeatureLabel("rateLimit") }}</strong>
              <small>保护登录、上传、重试和 AI 生成接口</small>
            </p>
            <p>
              <span>幂等</span>
              <strong>{{ securityFeatureLabel("idempotency") }}</strong>
              <small>重复上传时优先复用已有入库任务</small>
            </p>
            <p>
              <span>错误脱敏</span>
              <strong>{{ securityFeatureLabel("errorRedaction") }}</strong>
              <small>避免向前端暴露 provider 原始错误和敏感配置</small>
            </p>
          </div>
        </div>
      </section>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import AppLayout from "@/layouts/AppLayout.vue";
import { useAdminStore, type AdminAiDebugTab } from "@/stores/admin";
import { useAuthStore } from "@/stores/auth";
import type {
  AdminAgentLog,
  AdminAiDebugRagSummary,
  AdminUser,
  AdminRagDocument,
  AdminRagQualityItem,
  AdminRuntimeReplayStep,
  AdminWorkflowObservation
} from "@/api/admin";

type DebugRecord = Record<string, unknown>;

const auth = useAuthStore();
const admin = useAdminStore();
const isRestoringAuth = computed(() => auth.loading || (auth.isAuthenticated && !auth.user));
const userPageSizeOptions = [5, 10, 20];
const userPageSize = ref(10);
const userPage = ref(1);
const forceLogoutCandidate = ref<AdminUser | null>(null);
const aiDebugTabs: { key: AdminAiDebugTab; label: string }[] = [
  { key: "overview", label: "总览" },
  { key: "rag", label: "RAG 召回" },
  { key: "agent", label: "Agent 决策" },
  { key: "langgraph", label: "LangGraph" },
  { key: "diagnostics", label: "诊断建议" },
  { key: "raw", label: "原始日志" }
];

const userPageCount = computed(() => Math.max(1, Math.ceil(admin.filteredUsers.length / userPageSize.value)));
const paginatedUsers = computed(() => {
  const start = (userPage.value - 1) * userPageSize.value;
  return admin.filteredUsers.slice(start, start + userPageSize.value);
});

function openForceLogout(user: AdminUser): void {
  forceLogoutCandidate.value = user;
}

function closeForceLogout(): void {
  forceLogoutCandidate.value = null;
}

async function confirmForceLogout(): Promise<void> {
  if (!forceLogoutCandidate.value) return;
  await admin.forceLogoutUser(forceLogoutCandidate.value);
  closeForceLogout();
}

const debugRagSummary = computed<AdminAiDebugRagSummary[]>(() => {
  const rag = admin.selectedAiDebugDetail?.rag as DebugRecord | undefined;
  return Array.isArray(rag?.summary) ? (rag.summary as AdminAiDebugRagSummary[]) : [];
});
const debugRagItems = computed(() => {
  const rag = admin.selectedAiDebugDetail?.rag as DebugRecord | undefined;
  return Array.isArray(rag?.items) ? (rag.items as DebugRecord[]) : [];
});
const debugRagRawItems = computed(() => (debugRagSummary.value.length > 0 ? [] : debugRagItems.value));
const debugDiagnosticSummary = computed(() => {
  const detail = admin.selectedAiDebugDetail;
  if (!detail) return [];
  if (Array.isArray(detail.diagnosticSummary) && detail.diagnosticSummary.length > 0) {
    return detail.diagnosticSummary;
  }
  return detail.diagnostics.map((diagnostic) => ({ ...diagnostic, count: 1 }));
});
const aiDebugOverviewText = computed(() => {
  const action = debugText(admin.selectedAiDebugDetail?.agent, "nextActionLabel", "继续追问");
  const reason = debugText(admin.selectedAiDebugDetail?.agent, "reason", "");
  const ragHits = debugNumber(admin.selectedAiDebugDetail?.rag, "totalHitCount");
  if (reason && reason !== "暂无") {
    return `本轮主要动作是“${action}”，原因是：${reason}`;
  }
  return `本轮主要动作是“${action}”，RAG 总命中 ${ragHits} 条，系统根据当前面试上下文继续推进。`;
});
const workflowObservation = computed<AdminWorkflowObservation | null>(() => {
  return admin.selectedAiDebugDetail?.workflowObservation || null;
});
const workflowNodes = computed(() => workflowObservation.value?.nodes || []);
const workflowRagSummary = computed(() => workflowObservation.value?.ragSummary || []);
const workflowCheckpoint = computed(() => {
  return workflowObservation.value?.checkpoint || { exists: false };
});
const workflowQualityGatePassed = computed(() => {
  const gate = workflowObservation.value?.qualityGate;
  return Boolean(gate?.passed);
});
const infrastructure = computed(() => admin.config?.infrastructure || null);
const databaseInfraLabel = computed(() => {
  const database = infrastructure.value?.database;
  if (!database) return "未记录";
  if (database.isLocalSqlite) return "SQLite 本地开发";
  return `${database.dialect || "外部数据库"} 生产候选`;
});
const databaseMigrationLabel = computed(() => {
  const database = infrastructure.value?.database;
  if (!database) return "暂无迁移信息";
  return database.autoInitEnabled ? "本地自动初始化" : `迁移入口：${database.migrationTool || "alembic"}`;
});
const redisInfraLabel = computed(() => {
  const status = infrastructure.value?.redis?.status || "unknown";
  if (status === "disabled") return "Redis 未启用";
  if (status === "ok") return "Redis 正常";
  if (status === "error") return "Redis 异常";
  return `Redis ${status}`;
});
const redisInfraDetail = computed(() => {
  const redis = infrastructure.value?.redis;
  if (!redis) return "暂无 Redis 配置";
  if (redis.status === "error" && redis.error) return redis.error;
  return redis.url || "暂无 Redis URL";
});
const ingestionMaxDurationMs = computed(() => admin.ragIngestionTasks?.summary.maxDurationMs || 0);
const ingestionIdempotencyHitCount = computed(() => admin.ragIngestionTasks?.summary.idempotencyHitCount || 0);
const ingestionFailureStageItems = computed(() => {
  const stages = admin.ragIngestionTasks?.summary.failureStages || {};
  return Object.entries(stages).map(([stage, count]) => ({ stage, count }));
});
const celeryInfraLabel = computed(() => {
  const status = infrastructure.value?.celery?.status || "unknown";
  if (status === "eager") return "Celery eager";
  if (status === "configured") return "Celery worker";
  return `Celery ${status}`;
});
const celeryInfraDetail = computed(() => {
  const celery = infrastructure.value?.celery;
  if (!celery) return "暂无 Celery 配置";
  return celery.taskAlwaysEager ? "测试/本地同步执行任务" : "通过 broker 投递后台任务";
});
const celeryInfraModeLabel = computed(() => {
  const mode = infrastructure.value?.celery?.mode;
  if (!mode) return "";
  return `模式：${mode === "eager" ? "eager 本地测试" : "worker 异步模式"}`;
});
const celeryWorkerCommandLabel = computed(() => {
  const command = infrastructure.value?.celery?.workerCommand;
  return command ? `Worker：${command}` : "";
});
const celeryWorkerReadiness = computed(() => infrastructure.value?.celery?.workerReadiness || null);
const celeryWorkerReadinessStatusLabel = computed(() => {
  const readiness = celeryWorkerReadiness.value;
  if (!readiness) return "";
  if (readiness.mode === "eager") return "本地同步模式";
  return readiness.readyForWorker ? "Worker 配置就绪" : "Worker 配置不完整";
});
const celeryWorkerReadinessLabel = computed(() => celeryWorkerReadiness.value?.message || "");
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
const replaySummary = computed(() => {
  const langgraph = admin.selectedAiDebugDetail?.langgraph as DebugRecord | undefined;
  const replay = langgraph?.replaySummary;
  return replay && typeof replay === "object" ? (replay as DebugRecord) : {};
});
const hasReplaySummary = computed(() => Object.keys(replaySummary.value).length > 0);
const replaySummaryText = computed(() => {
  const value = replaySummary.value.summary;
  return typeof value === "string" && value.trim() ? value : "暂无 LangGraph 回放摘要。";
});
const replayTimeline = computed<AdminRuntimeReplayStep[]>(() => {
  const timeline = replaySummary.value.timeline;
  if (!Array.isArray(timeline)) return [];
  return timeline.map((item, index) => {
    const record = item && typeof item === "object" ? (item as DebugRecord) : {};
    return {
      step: Number(record.step ?? index + 1),
      node: String(record.node ?? "unknown"),
      title: String(record.title ?? "未知节点"),
      detail: String(record.detail ?? "暂无节点详情")
    };
  });
});
const replayRisks = computed(() => {
  const risks = replaySummary.value.risks;
  return Array.isArray(risks) ? risks.map(String).filter(Boolean) : [];
});
const replayNextActions = computed(() => {
  const actions = replaySummary.value.nextActions;
  return Array.isArray(actions) ? actions.map(String).filter(Boolean) : [];
});
const runtimeReport = computed(() => {
  const langgraph = admin.selectedAiDebugDetail?.langgraph as DebugRecord | undefined;
  const report = langgraph?.runtimeReport;
  return report && typeof report === "object" ? (report as DebugRecord) : {};
});
const hasRuntimeReport = computed(() => Object.keys(runtimeReport.value).length > 0);
const runtimeReportSummary = computed(() => {
  const value = runtimeReport.value.summary;
  return typeof value === "string" && value.trim() ? value : "暂无 Runtime 报告。";
});
const runtimeReportReasons = computed(() => {
  const items = runtimeReport.value.topQualityGateReasons;
  if (!Array.isArray(items)) return [];
  return items
    .map((item) => {
      const record = item && typeof item === "object" ? (item as DebugRecord) : {};
      return { reason: String(record.reason ?? ""), count: Number(record.count ?? 0) };
    })
    .filter((item) => item.reason);
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

function runtimeReportNumber(key: string): number {
  const value = runtimeReport.value[key];
  const numberValue = Number(value ?? 0);
  return Number.isFinite(numberValue) ? numberValue : 0;
}

function securityFeatureLabel(key: "tokenBlacklist" | "rateLimit" | "idempotency" | "errorRedaction"): string {
  const feature = admin.config?.security?.[key];
  if (!feature) return "未记录";
  const statusText = feature.enabled === false ? "未启用" : "已启用";
  return feature.backend ? `${statusText} · ${feature.backend}` : statusText;
}

function reviewActionLabel(value: string): string {
  const map: Record<string, string> = {
    resume: "恢复工作流",
    fallback_classic: "回退 classic",
    inspect_quality_gate: "检查质量门禁",
    continue_interview: "继续面试",
    switch_to_coach: "切换学习辅导",
    end_interview: "结束面试",
    inspect_timeline: "查看时间线"
  };
  return map[value] || value || "未知动作";
}

function debugRagKey(item: DebugRecord): string {
  return `${debugText(item, "retrieverLabel")}-${debugText(item, "queryText")}-${debugText(item, "hitCount", "0")}`;
}

function debugRagSummaryKey(item: AdminAiDebugRagSummary): string {
  return `${item.knowledgeBase || item.label || "unknown"}-${item.quality || "unknown"}`;
}

function qualityLevelLabel(value: unknown): string {
  const map: Record<string, string> = {
    good: "高相关",
    weak: "弱相关",
    miss: "空召回",
    empty: "空召回",
    unknown: "未评估"
  };
  const key = String(value || "unknown");
  return map[key] || key;
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
  if (item.recommendation) return item.recommendation;
  if (issueType === "empty_recall") return "补充岗位知识库或题库内容";
  if (issueType === "weak_recall") return "优化文档标题、metadata 或 chunk 内容";
  if (issueType === "unused_in_prompt") return "检查 Prompt 拼接逻辑或召回阈值";
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

function ingestionStatusLabel(value = ""): string {
  const map: Record<string, string> = {
    pending: "等待中",
    queued: "排队中",
    running: "处理中",
    succeeded: "已完成",
    success: "已完成",
    failed: "失败"
  };
  return map[value] || value || "未知状态";
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

.success-message {
  border: 1px solid rgba(18, 128, 92, 0.22);
  border-radius: var(--radius-sm);
  background: #ecfdf3;
  color: #027a48;
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
.pagination-bar button,
.table-action {
  min-height: 36px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  padding: 7px 10px;
}

.pagination-bar button,
.table-action {
  cursor: pointer;
}

.pagination-bar button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.table-action:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  background: rgba(15, 23, 42, 0.42);
  padding: 24px;
}

.confirm-modal {
  width: min(420px, 100%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: 0 24px 80px rgba(15, 23, 42, 0.22);
  padding: 22px;
}

.confirm-modal p {
  margin-top: 10px;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.modal-actions button {
  min-height: 38px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-accent);
  color: #fff;
  padding: 8px 14px;
  cursor: pointer;
}

.modal-actions .ghost-action {
  background: var(--color-surface);
  color: var(--color-text);
}

.list {
  display: grid;
  gap: 10px;
  margin-top: 16px;
}

.dashboard-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  margin-top: 14px;
  padding: 14px;
}

.dashboard-panel h3 {
  margin: 0 0 10px;
  font-size: 15px;
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

.debug-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0;
}

.debug-tabs button {
  min-height: 34px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 7px 11px;
}

.debug-tabs button[aria-selected="true"] {
  border-color: rgba(23, 92, 211, 0.46);
  background: #eef4ff;
  color: var(--color-accent);
  font-weight: 700;
}

.debug-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
}

.workflow-observation {
  border: 1px solid rgba(23, 92, 211, 0.25);
  border-radius: var(--radius-sm);
  background: #f5f8ff;
  margin-bottom: 12px;
  padding: 14px;
}

.workflow-observation h3 {
  margin: 0;
}

.workflow-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.workflow-metrics article {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  padding: 10px;
}

.workflow-metrics span {
  display: block;
  color: var(--color-text-muted);
  font-size: 12px;
  margin-bottom: 5px;
}

.workflow-node-list,
.workflow-rag-list,
.failure-stage-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.workflow-node-list span,
.workflow-rag-list span,
.failure-stage-list span {
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 12px;
  padding: 6px 9px;
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

.debug-subsection.compact {
  margin-top: 10px;
  padding-top: 10px;
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

.infra-panel {
  margin-top: 18px;
}

.infra-panel h3 {
  margin: 0;
  font-size: 16px;
}

.infra-panel small {
  display: block;
  margin-top: 6px;
  color: var(--color-text-muted);
  line-height: 1.5;
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
  .debug-grid,
  .workflow-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
