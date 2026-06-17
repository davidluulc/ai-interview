<template>
  <AppLayout>
    <section class="knowledge-page">
      <header class="page-header">
        <div>
          <p class="eyebrow">Knowledge Base</p>
          <h1>知识库</h1>
          <p>管理参与 RAG 检索的岗位资料、题库资料和候选人画像资料。</p>
        </div>
        <button data-testid="toggle-create-document" type="button" @click="showCreateForm = !showCreateForm">
          {{ showCreateForm ? "收起表单" : "新增文档" }}
        </button>
      </header>

      <section class="metrics">
        <article>
          <span>文档总数</span>
          <strong>{{ knowledge.documents.length }}</strong>
        </article>
        <article>
          <span>启用中</span>
          <strong>{{ knowledge.enabledCount }}</strong>
        </article>
        <article>
          <span>已归档</span>
          <strong>{{ knowledge.archivedCount }}</strong>
        </article>
      </section>

      <p v-if="knowledge.error" class="notice error">{{ knowledge.error }}</p>
      <p v-if="knowledge.loading" class="notice">知识库文档加载中...</p>

      <section v-if="showCreateForm" class="panel">
        <div class="section-title">
          <h2>新增知识库文档</h2>
          <span>手动录入当前阶段最稳妥，后续再扩展文件上传和异步入库。</span>
        </div>
        <form class="document-form" data-testid="submit-document" @submit.prevent="submitDocument">
          <label>
            标题
            <input v-model="documentForm.title" data-testid="document-title" type="text" placeholder="例如 FastAPI Depends" />
          </label>
          <label>
            知识库类型
            <select v-model="documentForm.knowledgeBase">
              <option value="role_knowledge">岗位知识库</option>
              <option value="question_bank">题库</option>
              <option value="candidate_memory">候选人画像</option>
            </select>
          </label>
          <label>
            可见性
            <select v-model="documentForm.visibility">
              <option value="private">仅自己可用</option>
              <option value="public">公共资料</option>
            </select>
          </label>
          <label>
            来源类型
            <input v-model="documentForm.sourceType" type="text" />
          </label>
          <label class="wide">
            内容
            <textarea
              v-model="documentForm.content"
              data-testid="document-content"
              rows="5"
              placeholder="写入岗位知识、题库样例或候选人画像内容"
            />
          </label>
          <label class="wide">
            metadata JSON
            <textarea
              v-model="documentForm.metadataJson"
              data-testid="document-metadata"
              rows="3"
              placeholder='{"role":"Python 后端","level":"实习"}'
            />
          </label>
          <p v-if="knowledge.metadataError" class="form-error">{{ knowledge.metadataError }}</p>
          <button type="submit" :disabled="knowledge.saving">保存文档</button>
        </form>
      </section>

      <section class="panel upload-panel">
        <div class="section-title">
          <div>
            <p class="section-kicker">文件导入</p>
            <h2>从本地文件生成知识库文档</h2>
          </div>
          <span>支持 txt、md、pdf</span>
        </div>
        <p class="empty">
          上传后会解析文本、清洗内容、切分 chunk，并进入现有 RAG 检索链路。当前阶段先做小文件同步导入，后续可迁移到 Celery 异步任务。
        </p>
        <form class="upload-form" data-testid="knowledge-upload-form" @submit.prevent="submitUpload">
          <label>
            文档标题
            <input v-model="uploadForm.title" data-testid="knowledge-upload-title" type="text" placeholder="例如 FastAPI 官方文档摘录" />
          </label>
          <label>
            知识库类型
            <select v-model="uploadForm.knowledgeBase">
              <option value="role_knowledge">岗位知识库</option>
              <option value="question_bank">题库</option>
              <option value="candidate_memory">候选人画像</option>
            </select>
          </label>
          <label>
            可见性
            <select v-model="uploadForm.visibility">
              <option value="private">仅自己可用</option>
              <option value="public">公共资料</option>
            </select>
          </label>
          <label>
            选择文件
            <input data-testid="knowledge-upload-file" type="file" accept=".txt,.md,.pdf" @change="onUploadFileChange" />
          </label>
          <label class="wide">
            metadata JSON
            <textarea
              v-model="uploadForm.metadataJson"
              data-testid="knowledge-upload-metadata"
              rows="3"
              placeholder='{"positionTag":"python_backend","category":"technical"}'
            />
          </label>
          <p v-if="knowledge.uploadError" class="form-error">{{ knowledge.uploadError }}</p>
          <button type="submit" :disabled="knowledge.uploading">{{ knowledge.uploading ? "导入中..." : "导入文件" }}</button>
        </form>
        <div v-if="knowledge.ingestionTask" class="ingestion-result">
          <strong>导入状态：{{ knowledge.ingestionTask.status }}</strong>
          <span v-if="ingestionPreview">
            文本长度 {{ ingestionPreview.textLength }}，chunk 数 {{ ingestionPreview.chunkCount }}
          </span>
          <span v-if="ingestionDocument">生成文档：{{ ingestionDocument.title || `#${ingestionDocument.id}` }}</span>
        </div>
        <div class="ingestion-history">
          <div class="section-title compact">
            <div>
              <p class="section-kicker">Ingestion Tasks</p>
              <h3>最近导入任务</h3>
            </div>
            <button type="button" class="secondary" @click="knowledge.loadIngestionTasks()">刷新</button>
          </div>
          <div v-if="knowledge.ingestionTasks.length" class="ingestion-task-list">
            <article v-for="task in knowledge.ingestionTasks" :key="task.taskId" class="ingestion-task-row">
              <div>
                <strong>{{ task.title || task.originalFilename || task.taskId }}</strong>
                <span>
                  {{ knowledgeBaseLabel(task.knowledgeBase || "") }} · {{ ingestionStatusLabel(task.status) }} · 重试
                  {{ task.retryCount || 0 }}/{{ task.maxRetries || 0 }}
                </span>
                <small v-if="task.error">{{ task.error }}</small>
                <small v-if="task.preview">
                  文本长度 {{ task.preview.textLength }}，chunk 数 {{ task.preview.chunkCount }}
                </small>
              </div>
              <button
                v-if="task.canRetry"
                :data-testid="`retry-ingestion-task-${task.taskId}`"
                type="button"
                class="secondary"
                :disabled="knowledge.retryingTaskId === task.taskId"
                @click="knowledge.retryTask(task.taskId)"
              >
                {{ knowledge.retryingTaskId === task.taskId ? "重试中..." : "重试" }}
              </button>
            </article>
          </div>
          <p v-else class="empty">还没有文件导入任务。</p>
        </div>
      </section>

      <section class="workspace-grid">
        <div class="main-column">
          <section class="panel">
            <div class="section-title">
              <h2>文档管理</h2>
              <span>{{ knowledge.filteredDocuments.length }} 个结果</span>
            </div>
            <div class="filters">
              <select data-testid="knowledge-base-filter" :value="knowledge.knowledgeBaseFilter" @change="updateKnowledgeBase">
                <option value="all">全部知识库</option>
                <option value="role_knowledge">岗位知识库</option>
                <option value="question_bank">题库</option>
                <option value="candidate_memory">候选人画像</option>
              </select>
              <select :value="knowledge.statusFilter" @change="updateStatusFilter">
                <option value="all">全部状态</option>
                <option value="enabled">启用中</option>
                <option value="disabled">已禁用</option>
                <option value="archived">已归档</option>
              </select>
              <select :value="knowledge.visibilityFilter" @change="updateVisibilityFilter">
                <option value="all">全部可见性</option>
                <option value="private">仅自己可用</option>
                <option value="public">公共资料</option>
              </select>
              <input
                data-testid="knowledge-search"
                :value="knowledge.searchKeyword"
                type="search"
                placeholder="搜索标题"
                @input="updateSearchKeyword"
              />
            </div>

            <div class="document-list">
              <article v-for="document in knowledge.filteredDocuments" :key="document.id" class="document-card">
                <div class="document-heading">
                  <div>
                    <strong>{{ document.title }}</strong>
                    <p>{{ knowledgeBaseLabel(document.knowledgeBase) }} · {{ document.sourceType || "manual" }}</p>
                  </div>
                  <span class="status-pill">{{ statusLabel(document.status) }}</span>
                </div>
                <p>
                  {{ visibilityLabel(document.visibility) }} · chunk {{ document.chunkCount || 0 }} · 重复
                  {{ document.duplicateChunkCount || 0 }} · 更新 {{ formatDate(document.updatedAt) }}
                </p>
                <div class="actions">
                  <button :data-testid="`open-document-${document.id}`" type="button" @click="knowledge.loadDocumentDetail(document.id)">
                    查看详情
                  </button>
                  <button type="button" @click="knowledge.updateStatus(document.id, 'enabled')">启用</button>
                  <button :data-testid="`disable-document-${document.id}`" type="button" @click="knowledge.updateStatus(document.id, 'disabled')">
                    禁用
                  </button>
                  <button type="button" @click="knowledge.updateStatus(document.id, 'archived')">归档</button>
                  <button :data-testid="`delete-document-${document.id}`" class="danger" type="button" @click="confirmDelete(document.id)">
                    删除
                  </button>
                </div>
              </article>
              <p v-if="!knowledge.loading && knowledge.filteredDocuments.length === 0" class="empty">
                暂无知识库文档。可以先手动录入一条岗位知识或题库样例。
              </p>
            </div>
          </section>

          <section class="panel">
            <div class="section-title">
              <h2>RAG 调试与解释</h2>
              <span>观察三类 RAG 如何进入面试上下文</span>
            </div>
            <form class="debug-form" data-testid="run-rag-debug" @submit.prevent="runDebug">
              <input v-model="debugForm.candidateName" placeholder="候选人姓名" />
              <input v-model="debugForm.role" data-testid="debug-role" placeholder="目标岗位" />
              <input v-model="debugForm.positionTag" placeholder="岗位标签" />
              <input v-model="debugForm.stage" data-testid="debug-stage" placeholder="面试阶段" />
              <textarea v-model="debugForm.resume" placeholder="简历摘要" rows="3" />
              <textarea v-model="debugForm.jd" placeholder="岗位 JD" rows="3" />
              <button type="submit" :disabled="knowledge.debugLoading">查看当前检索上下文</button>
            </form>

            <div v-if="knowledge.debugResult" class="debug-result">
              <article>
                <h3>岗位知识库命中</h3>
                <p>{{ hitSummary(knowledge.debugResult.roleKnowledge) }}</p>
              </article>
              <article>
                <h3>题库命中</h3>
                <p>{{ hitSummary(knowledge.debugResult.questionBank) }}</p>
              </article>
              <article>
                <h3>候选人画像命中</h3>
                <p>{{ hitSummary(knowledge.debugResult.candidateMemory) }}</p>
              </article>
              <details class="raw-debug">
                <summary>召回质量与解释</summary>
                <pre>{{ JSON.stringify({ quality: knowledge.debugResult.quality, explanations: knowledge.debugResult.explanations }, null, 2) }}</pre>
              </details>
            </div>
          </section>
        </div>

        <aside class="side-column">
          <section class="panel">
            <div class="section-title">
              <h2>文档详情</h2>
            </div>
            <div v-if="knowledge.selectedDetail" class="detail">
              <strong>{{ knowledge.selectedDetail.document.title }}</strong>
              <p>
                {{ knowledgeBaseLabel(knowledge.selectedDetail.document.knowledgeBase) }} ·
                {{ statusLabel(knowledge.selectedDetail.document.status) }} ·
                {{ visibilityLabel(knowledge.selectedDetail.document.visibility) }}
              </p>
              <article v-for="chunk in knowledge.selectedDetail.chunks" :key="chunk.id" class="chunk-card">
                <span>#{{ chunk.chunkIndex }} · {{ chunk.chunkHash || "no hash" }}</span>
                <p>{{ chunk.content }}</p>
                <details>
                  <summary>metadata</summary>
                  <pre>{{ JSON.stringify(chunk.metadata || {}, null, 2) }}</pre>
                </details>
              </article>
            </div>
            <p v-else class="empty">选择一份文档后，可以查看它被切分出来的 chunks。</p>
          </section>
        </aside>
      </section>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import AppLayout from "@/layouts/AppLayout.vue";
import type {
  KnowledgeBaseType,
  RagDocument,
  RagDocumentStatus,
  RagDocumentVisibility,
  RagDebugPayload
} from "@/api/knowledge";
import { useKnowledgeStore } from "@/stores/knowledge";
import type { KnowledgeBaseFilter, DocumentStatusFilter, DocumentVisibilityFilter } from "@/stores/knowledge";

const knowledge = useKnowledgeStore();
const showCreateForm = ref(false);

const documentForm = reactive({
  title: "",
  knowledgeBase: "role_knowledge" as KnowledgeBaseType,
  sourceType: "manual",
  content: "",
  visibility: "private" as RagDocumentVisibility,
  metadataJson: ""
});

const uploadForm = reactive({
  title: "",
  knowledgeBase: "role_knowledge" as KnowledgeBaseType,
  visibility: "private" as RagDocumentVisibility,
  metadataJson: "",
  file: null as File | null
});

const debugForm = reactive<RagDebugPayload>({
  candidateName: "",
  role: "",
  positionTag: "",
  resume: "",
  jd: "",
  stage: ""
});

const ingestionPreview = computed(() => knowledge.ingestionTask?.preview || knowledge.ingestionTask?.result?.preview || null);
const ingestionDocument = computed<RagDocument | null>(
  () => knowledge.ingestionTask?.document || knowledge.ingestionTask?.result?.document || null
);

onMounted(() => {
  void knowledge.loadDocuments();
  void knowledge.loadIngestionTasks();
});

async function submitDocument(): Promise<void> {
  const created = await knowledge.createDocumentFromForm({ ...documentForm });
  if (!created) return;
  documentForm.title = "";
  documentForm.content = "";
  documentForm.metadataJson = "";
  showCreateForm.value = false;
}

async function submitUpload(): Promise<void> {
  const uploaded = await knowledge.uploadFile({ ...uploadForm });
  if (!uploaded) return;
  uploadForm.title = "";
  uploadForm.metadataJson = "";
  uploadForm.file = null;
}

function onUploadFileChange(event: Event): void {
  const files = (event.target as HTMLInputElement).files;
  uploadForm.file = files?.[0] || null;
  if (!uploadForm.title && uploadForm.file) {
    uploadForm.title = uploadForm.file.name.replace(/\.[^.]+$/, "");
  }
}

function runDebug(): Promise<void> {
  return knowledge.runDebug({ ...debugForm });
}

function confirmDelete(documentId: number): void {
  if (window.confirm("确定删除这份知识库文档吗？删除后对应 chunks 也会被移除。")) {
    void knowledge.removeDocument(documentId);
  }
}

function updateKnowledgeBase(event: Event): void {
  knowledge.setFilters({
    knowledgeBase: selectValue(event) as KnowledgeBaseFilter,
    status: "all",
    visibility: "all",
    searchKeyword: knowledge.searchKeyword
  });
}

function updateStatusFilter(event: Event): void {
  knowledge.setFilters({
    knowledgeBase: knowledge.knowledgeBaseFilter,
    status: selectValue(event) as DocumentStatusFilter,
    visibility: knowledge.visibilityFilter,
    searchKeyword: knowledge.searchKeyword
  });
}

function updateVisibilityFilter(event: Event): void {
  knowledge.setFilters({
    knowledgeBase: knowledge.knowledgeBaseFilter,
    status: knowledge.statusFilter,
    visibility: selectValue(event) as DocumentVisibilityFilter,
    searchKeyword: knowledge.searchKeyword
  });
}

function updateSearchKeyword(event: Event): void {
  knowledge.setFilters({
    knowledgeBase: knowledge.knowledgeBaseFilter,
    status: knowledge.statusFilter,
    visibility: knowledge.visibilityFilter,
    searchKeyword: inputValue(event)
  });
}

function selectValue(event: Event): string {
  return (event.target as HTMLSelectElement).value;
}

function inputValue(event: Event): string {
  return (event.target as HTMLInputElement).value;
}

function knowledgeBaseLabel(value: string): string {
  const labels: Record<string, string> = {
    role_knowledge: "岗位知识库",
    question_bank: "题库",
    candidate_memory: "候选人画像"
  };
  return labels[value] || value || "未知知识库";
}

function statusLabel(value: string): string {
  const labels: Record<string, string> = {
    enabled: "启用中",
    disabled: "已禁用",
    archived: "已归档"
  };
  return labels[value] || value || "未知状态";
}

function ingestionStatusLabel(value: string): string {
  const labels: Record<string, string> = {
    pending: "等待中",
    running: "处理中",
    succeeded: "已完成",
    success: "已完成",
    failed: "失败"
  };
  return labels[value] || value || "未知状态";
}

function visibilityLabel(value: string): string {
  const labels: Record<string, string> = {
    private: "仅自己可用",
    public: "公共资料"
  };
  return labels[value] || value || "未知可见性";
}

function formatDate(value?: string | null): string {
  return value ? value.slice(0, 10) : "未知";
}

function hitSummary(value: unknown[] | undefined): string {
  if (!Array.isArray(value) || value.length === 0) {
    return "暂无命中";
  }
  return value
    .slice(0, 3)
    .map((item) => {
      if (item && typeof item === "object" && "title" in item) {
        return String((item as { title?: unknown }).title || "未命名资料");
      }
      return "命中资料";
    })
    .join("、");
}
</script>

<style scoped>
.knowledge-page {
  display: grid;
  gap: 22px;
  max-width: 1200px;
  min-width: 0;
}

.page-header,
.section-title,
.document-heading,
.actions,
.metrics,
.filters {
  display: flex;
  gap: 12px;
}

.page-header {
  align-items: flex-end;
  justify-content: space-between;
}

.page-header p,
.document-card p,
.detail p,
.empty,
.notice,
.section-title span {
  color: var(--color-text-muted);
  line-height: 1.7;
}

.eyebrow {
  color: var(--color-accent);
  font-size: 13px;
  font-weight: 700;
  margin: 0;
}

h1,
h2,
h3,
p {
  margin: 0;
}

h1 {
  font-size: clamp(34px, 5vw, 52px);
  line-height: 1.05;
  margin-top: 8px;
}

h2 {
  font-size: 20px;
}

h3 {
  font-size: 15px;
}

button,
input,
select,
textarea {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font: inherit;
}

button {
  background: var(--color-text);
  color: var(--color-surface);
  cursor: pointer;
  font-weight: 700;
  padding: 10px 13px;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

button.danger {
  background: #b42318;
}

input,
select,
textarea {
  background: var(--color-surface);
  color: var(--color-text);
  min-height: 42px;
  padding: 10px 12px;
}

textarea {
  resize: vertical;
}

.metrics {
  flex-wrap: wrap;
}

.metrics article,
.panel,
.document-card,
.chunk-card,
.debug-result article {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.metrics article {
  min-width: 150px;
  padding: 16px;
}

.metrics span {
  color: var(--color-text-muted);
  display: block;
  font-size: 13px;
  margin-bottom: 6px;
}

.metrics strong {
  font-size: 28px;
}

.panel {
  display: grid;
  gap: 16px;
  min-width: 0;
  padding: 22px;
}

.section-title {
  align-items: center;
  justify-content: space-between;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  gap: 22px;
  align-items: start;
}

.main-column,
.side-column,
.document-list,
.detail,
.debug-result {
  display: grid;
  gap: 14px;
  min-width: 0;
}

.filters {
  flex-wrap: wrap;
}

.filters input {
  min-width: min(260px, 100%);
}

.document-form,
.upload-form,
.debug-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

label {
  display: grid;
  gap: 7px;
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 700;
}

.wide,
.form-error,
.debug-form button,
.upload-form button {
  grid-column: 1 / -1;
}

.form-error,
.error {
  color: #b42318;
}

.notice {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  padding: 12px 14px;
}

.document-card,
.chunk-card,
.debug-result article {
  display: grid;
  gap: 10px;
  padding: 15px;
}

.document-heading {
  align-items: flex-start;
  justify-content: space-between;
}

.status-pill {
  border-radius: 999px;
  background: #ecfdf3;
  color: #027a48;
  font-size: 12px;
  font-weight: 700;
  padding: 5px 9px;
  white-space: nowrap;
}

.actions {
  flex-wrap: wrap;
}

.actions button {
  background: var(--color-surface-muted);
  color: var(--color-text);
}

.actions .danger {
  background: #fff3f0;
  color: #b42318;
}

.chunk-card {
  background: var(--color-surface-muted);
}

.chunk-card span {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
}

details {
  min-width: 0;
}

summary {
  cursor: pointer;
  font-weight: 700;
}

pre {
  max-width: 100%;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.raw-debug {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-muted);
  padding: 12px;
}

.section-kicker {
  color: var(--color-accent);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  margin-bottom: 4px;
}

.upload-panel {
  border-color: #b9d7ff;
}

.ingestion-result,
.ingestion-task-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface-muted);
  padding: 12px;
}

.ingestion-history,
.ingestion-task-list,
.ingestion-task-row > div {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.section-title.compact {
  align-items: center;
}

button.secondary {
  background: var(--color-surface-muted);
  color: var(--color-text);
}

.ingestion-task-row {
  align-items: center;
  justify-content: space-between;
}

.ingestion-task-row span,
.ingestion-task-row small {
  color: var(--color-text-muted);
  line-height: 1.6;
}

@media (max-width: 960px) {
  .page-header,
  .section-title,
  .document-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .workspace-grid,
  .document-form,
  .upload-form,
  .debug-form {
    grid-template-columns: 1fr;
  }
}
</style>
