<template>
  <AppLayout>
    <section class="knowledge-page">
      <header class="page-head">
        <div>
          <h1>知识库</h1>
          <p class="subtitle">管理参与 RAG 检索的岗位资料、题库资料和候选人画像资料。</p>
        </div>
        <BrutButton
          variant="ghost"
          data-testid="toggle-create-document"
          type="button"
          @click="showCreateForm = !showCreateForm"
        >
          {{ showCreateForm ? "收起表单" : "新增文档" }}
        </BrutButton>
      </header>

      <section class="metrics" aria-label="知识库概览">
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

      <p v-if="knowledge.error" class="notice notice--error">{{ knowledge.error }}</p>
      <p v-if="knowledge.loading" class="notice notice--loading">知识库文档加载中...</p>

      <section v-if="showCreateForm" class="form-panel">
        <div class="section-head">
          <h2>新增知识库文档</h2>
          <span>手动录入当前阶段最稳妥，后续再扩展文件上传和异步入库。</span>
        </div>
        <form class="document-form" data-testid="submit-document" @submit.prevent="submitDocument">
          <BrutField
            v-model="documentForm.title"
            data-testid="document-title"
            label="标题"
            placeholder="例如 FastAPI Depends"
            type="text"
          />
          <label class="field-block">
            <span>知识库类型</span>
            <select v-model="documentForm.knowledgeBase">
              <option value="role_knowledge">岗位知识库</option>
              <option value="question_bank">题库</option>
              <option value="candidate_memory">候选人画像</option>
            </select>
          </label>
          <label class="field-block">
            <span>可见性</span>
            <select v-model="documentForm.visibility">
              <option value="private">仅自己可用</option>
              <option value="public">公共资料</option>
            </select>
          </label>
          <BrutField v-model="documentForm.sourceType" label="来源类型" type="text" />
          <label class="field-block wide">
            <span>内容</span>
            <textarea
              v-model="documentForm.content"
              data-testid="document-content"
              rows="5"
              placeholder="写入岗位知识、题库样例或候选人画像内容"
            />
          </label>
          <BrutButton
            class="wide"
            variant="ghost"
            data-testid="document-advanced-toggle"
            type="button"
            @click="showDocumentAdvanced = !showDocumentAdvanced"
          >
            {{ showDocumentAdvanced ? "收起高级设置" : "高级设置" }}
          </BrutButton>
          <label v-if="showDocumentAdvanced" class="field-block wide">
            <span>metadata JSON</span>
            <textarea
              v-model="documentForm.metadataJson"
              data-testid="document-metadata"
              rows="3"
              placeholder='{"role":"Python 后端","level":"实习"}'
            />
          </label>
          <p v-if="showDocumentAdvanced && knowledge.metadataError" class="form-error wide">{{ knowledge.metadataError }}</p>
          <BrutButton variant="primary" type="submit" :disabled="knowledge.saving">保存文档</BrutButton>
        </form>
      </section>

      <BrutPanel title="文件导入" class="upload-panel">
        <div class="upload-body">
          <div class="section-head">
            <h2>从本地文件生成知识库文档</h2>
            <span>支持 txt、md、pdf</span>
          </div>
          <p class="panel-note">
            上传后会创建入库任务，由 Celery eager 或 worker 模式执行文本解析、清洗、chunk 切分，并进入现有 RAG 检索链路。
          </p>
          <form class="upload-form" data-testid="knowledge-upload-form" @submit.prevent="submitUpload">
            <BrutField
              v-model="uploadForm.title"
              data-testid="knowledge-upload-title"
              label="文档标题"
              placeholder="例如 FastAPI 官方文档摘录"
              type="text"
            />
            <label class="field-block">
              <span>知识库类型</span>
              <select v-model="uploadForm.knowledgeBase">
                <option value="role_knowledge">岗位知识库</option>
                <option value="question_bank">题库</option>
                <option value="candidate_memory">候选人画像</option>
              </select>
            </label>
            <label class="field-block">
              <span>可见性</span>
              <select v-model="uploadForm.visibility">
                <option value="private">仅自己可用</option>
                <option value="public">公共资料</option>
              </select>
            </label>
            <div class="field-block">
              <span>选择文件</span>
              <div class="file-picker">
                <label class="file-picker__button">
                  选择文件
                  <input
                    data-testid="knowledge-upload-file"
                    type="file"
                    accept=".txt,.md,.pdf"
                    class="file-picker__input"
                    @change="onUploadFileChange"
                  />
                </label>
                <span class="file-picker__name" :class="{ 'file-picker__name--set': uploadFileName }">
                  {{ uploadFileName || "未选择文件" }}
                </span>
              </div>
            </div>
            <BrutButton
              class="wide"
              variant="ghost"
              data-testid="upload-advanced-toggle"
              type="button"
              @click="showUploadAdvanced = !showUploadAdvanced"
            >
              {{ showUploadAdvanced ? "收起高级设置" : "高级设置" }}
            </BrutButton>
            <label v-if="showUploadAdvanced" class="field-block wide">
              <span>metadata JSON</span>
              <textarea
                v-model="uploadForm.metadataJson"
                data-testid="knowledge-upload-metadata"
                rows="3"
                placeholder='{"positionTag":"python_backend","category":"technical"}'
              />
            </label>
            <p v-if="knowledge.uploadError" class="form-error wide">{{ knowledge.uploadError }}</p>
            <BrutButton variant="primary" type="submit" :disabled="knowledge.uploading">
              {{ knowledge.uploading ? "导入中..." : "导入文件" }}
            </BrutButton>
          </form>
          <div v-if="knowledge.ingestionTask" class="ingestion-result">
            <strong>导入状态：</strong><BrutChip
              :label="ingestionStatusLabel(knowledge.ingestionTask.status)"
              :tone="ingestionStatusTone(knowledge.ingestionTask.status)"
            />
            <span v-if="ingestionPreview">
              文本长度 <span class="num">{{ ingestionPreview.textLength }}</span>，chunk 数
              <span class="num">{{ ingestionPreview.chunkCount }}</span>
            </span>
            <span v-if="ingestionDocument">生成文档：{{ ingestionDocument.title || `#${ingestionDocument.id}` }}</span>
          </div>
          <div class="ingestion-history">
            <div class="section-head compact">
              <h3>最近导入任务</h3>
              <BrutButton variant="ghost" type="button" @click="knowledge.loadIngestionTasks()">刷新</BrutButton>
            </div>
            <div v-if="knowledge.ingestionTasks.length" class="task-list">
              <article v-for="task in knowledge.ingestionTasks" :key="task.taskId" class="task-row">
                <div class="task-row__main">
                  <strong>{{ task.title || task.originalFilename || task.taskId }}</strong>
                  <span>{{ knowledgeBaseLabel(task.knowledgeBase || "") }} · <BrutChip :label="ingestionStatusLabel(task.status)" :tone="ingestionStatusTone(task.status)" /> · 重试 <span class="num">{{ task.retryCount || 0 }}</span>/<span class="num">{{ task.maxRetries || 0 }}</span></span>
                  <small v-if="task.error">{{ task.error }}</small>
                  <small v-if="task.preview">
                    文本长度 <span class="num">{{ task.preview.textLength }}</span>，chunk 数
                    <span class="num">{{ task.preview.chunkCount }}</span>
                  </small>
                </div>
                <BrutButton
                  v-if="task.canRetry"
                  :data-testid="`retry-ingestion-task-${task.taskId}`"
                  variant="ghost"
                  type="button"
                  :disabled="knowledge.retryingTaskId === task.taskId"
                  @click="knowledge.retryTask(task.taskId)"
                >
                  {{ knowledge.retryingTaskId === task.taskId ? "重试中..." : "重试" }}
                </BrutButton>
              </article>
            </div>
            <p v-else class="empty">还没有文件导入任务。</p>
          </div>
        </div>
      </BrutPanel>

      <section class="workspace-grid">
        <div class="main-column">
          <section class="ledger-section">
            <div class="section-head">
              <h2>文档管理</h2>
              <span class="section-count"><span class="num">{{ knowledge.filteredDocuments.length }}</span> 个结果</span>
            </div>
            <div class="filters">
              <label class="filter-block">
                <span>知识库</span>
                <select data-testid="knowledge-base-filter" :value="knowledge.knowledgeBaseFilter" @change="updateKnowledgeBase">
                  <option value="all">全部知识库</option>
                  <option value="role_knowledge">岗位知识库</option>
                  <option value="question_bank">题库</option>
                  <option value="candidate_memory">候选人画像</option>
                </select>
              </label>
              <label class="filter-block">
                <span>状态</span>
                <select :value="knowledge.statusFilter" @change="updateStatusFilter">
                  <option value="all">全部状态</option>
                  <option value="enabled">启用中</option>
                  <option value="disabled">已禁用</option>
                  <option value="archived">已归档</option>
                </select>
              </label>
              <label class="filter-block">
                <span>可见性</span>
                <select :value="knowledge.visibilityFilter" @change="updateVisibilityFilter">
                  <option value="all">全部可见性</option>
                  <option value="private">仅自己可用</option>
                  <option value="public">公共资料</option>
                </select>
              </label>
              <label class="filter-block">
                <span>搜索</span>
                <input
                  data-testid="knowledge-search"
                  :value="knowledge.searchKeyword"
                  type="search"
                  placeholder="搜索标题"
                  @input="updateSearchKeyword"
                />
              </label>
            </div>

            <div class="document-list">
              <article v-for="document in knowledge.filteredDocuments" :key="document.id" class="doc-row">
                <div class="doc-row__main">
                  <div class="doc-row__head">
                    <strong>{{ document.title }}</strong>
                    <BrutChip :label="statusLabel(document.status)" :tone="documentStatusTone(document.status)" />
                  </div>
                  <p class="doc-row__meta">
                    {{ knowledgeBaseLabel(document.knowledgeBase) }} · {{ document.sourceType || "manual" }} ·
                    {{ visibilityLabel(document.visibility) }}
                  </p>
                  <p class="doc-row__data">
                    chunk <span class="num">{{ document.chunkCount || 0 }}</span> · 重复
                    <span class="num">{{ document.duplicateChunkCount || 0 }}</span> · 更新
                    <span class="num">{{ formatDate(document.updatedAt) }}</span>
                  </p>
                </div>
                <div class="doc-row__actions">
                  <BrutButton
                    :data-testid="`open-document-${document.id}`"
                    variant="primary"
                    type="button"
                    @click="knowledge.loadDocumentDetail(document.id)"
                  >
                    查看详情
                  </BrutButton>
                  <BrutButton variant="ghost" type="button" @click="knowledge.updateStatus(document.id, 'enabled')">启用</BrutButton>
                  <BrutButton
                    :data-testid="`disable-document-${document.id}`"
                    variant="ghost"
                    type="button"
                    @click="knowledge.updateStatus(document.id, 'disabled')"
                  >
                    禁用
                  </BrutButton>
                  <BrutButton variant="ghost" type="button" @click="knowledge.updateStatus(document.id, 'archived')">归档</BrutButton>
                  <BrutButton
                    :data-testid="`delete-document-${document.id}`"
                    variant="danger"
                    type="button"
                    @click="confirmDelete(document.id)"
                  >
                    删除
                  </BrutButton>
                </div>
              </article>
              <p v-if="!knowledge.loading && knowledge.filteredDocuments.length === 0" class="empty">
                暂无知识库文档。可以先手动录入一条岗位知识或题库样例。
              </p>
            </div>
          </section>

          <BrutButton
            class="debug-toggle"
            variant="ghost"
            data-testid="rag-debug-toggle"
            type="button"
            @click="showDebugPanel = !showDebugPanel"
          >
            {{ showDebugPanel ? "收起高级调试" : "高级调试" }}
          </BrutButton>

          <BrutPanel v-if="showDebugPanel" title="RAG 调试与解释">
            <div class="debug-body">
              <p class="panel-note">观察三类 RAG 如何进入面试上下文</p>
              <form class="debug-form" data-testid="run-rag-debug" @submit.prevent="runDebug">
                <label class="field-block">
                  <span>候选人姓名</span>
                  <input v-model="debugForm.candidateName" placeholder="候选人姓名" />
                </label>
                <label class="field-block">
                  <span>目标岗位</span>
                  <input v-model="debugForm.role" data-testid="debug-role" placeholder="目标岗位" />
                </label>
                <label class="field-block">
                  <span>岗位标签</span>
                  <input v-model="debugForm.positionTag" placeholder="岗位标签" />
                </label>
                <label class="field-block">
                  <span>面试阶段</span>
                  <input v-model="debugForm.stage" data-testid="debug-stage" placeholder="面试阶段" />
                </label>
                <label class="field-block wide">
                  <span>简历摘要</span>
                  <textarea v-model="debugForm.resume" placeholder="简历摘要" rows="3" />
                </label>
                <label class="field-block wide">
                  <span>岗位 JD</span>
                  <textarea v-model="debugForm.jd" placeholder="岗位 JD" rows="3" />
                </label>
                <BrutButton variant="primary" type="submit" :disabled="knowledge.debugLoading">查看当前检索上下文</BrutButton>
              </form>

              <div v-if="knowledge.debugResult" class="debug-result">
                <article class="hit-group">
                  <h3>岗位知识库命中</h3>
                  <div class="hit-list">
                    <article
                      v-for="(hit, index) in hitListOf(knowledge.debugResult.roleKnowledge)"
                      :key="index"
                      class="hit-row"
                    >
                      <span>{{ hitTitle(hit) }}</span>
                      <ChunkChip v-if="hitScore(hit) !== null" label="命中分" :score="hitScore(hit) ?? 0" />
                    </article>
                    <p v-if="hitListOf(knowledge.debugResult.roleKnowledge).length === 0" class="empty">暂无命中</p>
                  </div>
                </article>
                <article class="hit-group">
                  <h3>题库命中</h3>
                  <div class="hit-list">
                    <article
                      v-for="(hit, index) in hitListOf(knowledge.debugResult.questionBank)"
                      :key="index"
                      class="hit-row"
                    >
                      <span>{{ hitTitle(hit) }}</span>
                      <ChunkChip v-if="hitScore(hit) !== null" label="命中分" :score="hitScore(hit) ?? 0" />
                    </article>
                    <p v-if="hitListOf(knowledge.debugResult.questionBank).length === 0" class="empty">暂无命中</p>
                  </div>
                </article>
                <article class="hit-group">
                  <h3>候选人画像命中</h3>
                  <div class="hit-list">
                    <article
                      v-for="(hit, index) in hitListOf(knowledge.debugResult.candidateMemory)"
                      :key="index"
                      class="hit-row"
                    >
                      <span>{{ hitTitle(hit) }}</span>
                      <ChunkChip v-if="hitScore(hit) !== null" label="命中分" :score="hitScore(hit) ?? 0" />
                    </article>
                    <p v-if="hitListOf(knowledge.debugResult.candidateMemory).length === 0" class="empty">暂无命中</p>
                  </div>
                </article>
                <details class="raw-debug">
                  <summary>召回质量与解释</summary>
                  <pre>{{ JSON.stringify({ quality: knowledge.debugResult.quality, explanations: knowledge.debugResult.explanations }, null, 2) }}</pre>
                </details>
              </div>
            </div>
          </BrutPanel>
        </div>

        <aside class="side-column">
          <BrutPanel title="文档详情">
            <div v-if="knowledge.selectedDetail" class="detail">
              <strong>{{ knowledge.selectedDetail.document.title }}</strong>
              <p class="detail-meta">
                {{ knowledgeBaseLabel(knowledge.selectedDetail.document.knowledgeBase) }} ·<BrutChip
                  :label="statusLabel(knowledge.selectedDetail.document.status)"
                  :tone="documentStatusTone(knowledge.selectedDetail.document.status)"
                />· {{ visibilityLabel(knowledge.selectedDetail.document.visibility) }}
              </p>
              <article v-for="chunk in knowledge.selectedDetail.chunks" :key="chunk.id" class="chunk-row">
                <div class="chunk-row__head">
                  <span>#{{ chunk.chunkIndex }} · {{ chunk.chunkHash || "no hash" }}</span>
                  <BrutChip
                    v-if="chunk.embeddingStatus"
                    :label="embeddingStatusLabel(chunk.embeddingStatus)"
                    :tone="embeddingStatusTone(chunk.embeddingStatus)"
                  />
                </div>
                <p>{{ chunk.content }}</p>
                <details>
                  <summary>metadata</summary>
                  <pre>{{ JSON.stringify(chunk.metadata || {}, null, 2) }}</pre>
                </details>
              </article>
            </div>
            <p v-else class="empty">选择一份文档后，可以查看它被切分出来的 chunks。</p>
          </BrutPanel>
        </aside>
      </section>
    </section>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import BrutButton from "@/components/brut/BrutButton.vue";
import BrutChip from "@/components/brut/BrutChip.vue";
import BrutField from "@/components/brut/BrutField.vue";
import BrutPanel from "@/components/brut/BrutPanel.vue";
import ChunkChip from "@/components/brut/ChunkChip.vue";
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
const showDocumentAdvanced = ref(false);
const showUploadAdvanced = ref(false);
const showDebugPanel = ref(false);
const uploadFileName = ref("");

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
  uploadFileName.value = "";
}

function onUploadFileChange(event: Event): void {
  const files = (event.target as HTMLInputElement).files;
  uploadForm.file = files?.[0] || null;
  uploadFileName.value = uploadForm.file?.name || "";
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
    queued: "排队中",
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

/* 模板绑定辅助：状态值域来自真实接口（api/knowledge.ts + backend rag_store/vector_store）。 */
type ChipTone = "ok" | "warn" | "danger" | "info" | "neutral";

/* 文档 status 真实值域：enabled / disabled / archived。启用=语义绿，禁用/归档为非活跃中性态。 */
function documentStatusTone(value: string): ChipTone {
  if (value === "enabled") return "ok";
  return "neutral";
}

/* 摄取任务 status 真实值域：pending / queued / running / succeeded / success / failed。 */
function ingestionStatusTone(value: string): ChipTone {
  if (value === "succeeded" || value === "success") return "ok";
  if (value === "running") return "warn";
  if (value === "failed") return "danger";
  return "neutral";
}

/* chunk embeddingStatus 真实值域：pending / ready / empty / failed。 */
function embeddingStatusTone(value: string): ChipTone {
  if (value === "ready") return "ok";
  if (value === "pending") return "warn";
  if (value === "failed") return "danger";
  return "neutral";
}

function embeddingStatusLabel(value: string): string {
  const labels: Record<string, string> = {
    ready: "就绪",
    pending: "等待中",
    empty: "无向量",
    failed: "失败"
  };
  return labels[value] || value;
}

function hitListOf(value: unknown[] | undefined): unknown[] {
  return Array.isArray(value) ? value : [];
}

function hitTitle(item: unknown): string {
  if (item && typeof item === "object" && "title" in item) {
    return String((item as { title?: unknown }).title || "未命名资料");
  }
  return "命中资料";
}

/* 仅当命中对象带有限定数值 score（后端 BM25 / 混合归一 / 重排分）时才渲染 ChunkChip。 */
function hitScore(item: unknown): number | null {
  if (item && typeof item === "object" && "score" in item) {
    const score = (item as { score?: unknown }).score;
    if (typeof score === "number" && Number.isFinite(score)) {
      return score;
    }
  }
  return null;
}

function formatDate(value?: string | null): string {
  return value ? value.slice(0, 10) : "未知";
}
</script>

<style scoped>
.knowledge-page {
  display: grid;
  gap: var(--s6);
  max-width: 1200px;
  min-width: 0;
  font-family: var(--font-ui);
  color: var(--ink);
}

h2,
h3,
p {
  margin: 0;
}

.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s5);
}

.page-head h1 {
  margin: 0 0 var(--s2);
  font-size: var(--text-page);
  font-weight: 900;
  line-height: 1.1;
}

.subtitle {
  margin: 0;
  max-width: 56ch;
  color: var(--ink-soft);
  font-size: var(--text-strong);
  font-weight: 700;
  line-height: 1.6;
}

/* 概览数字：静态盒 2px 墨边，无投影；数字用等宽字。 */
.metrics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--s3);
}

.metrics article {
  min-width: 150px;
  border: var(--line);
  background: var(--panel);
  padding: var(--s4);
}

.metrics span {
  display: block;
  margin-bottom: var(--s2);
  color: var(--ink-soft);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1.2;
}

.metrics strong {
  font-family: var(--font-mono);
  font-size: var(--text-page);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.notice {
  width: fit-content;
  border: var(--line);
  background: var(--panel);
  color: var(--ink);
  font-size: var(--text-strong);
  font-weight: 800;
  padding: var(--s4);
}

.notice--error {
  background: var(--danger);
  color: var(--action-ink);
}

.notice--loading {
  border-style: dashed;
  color: var(--ink-soft);
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--s3);
}

.section-head h2 {
  font-size: var(--text-section);
  font-weight: 900;
  line-height: 1.2;
}

.section-head h3 {
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.2;
}

.section-head > span {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
}

.section-head.compact {
  align-items: center;
}

.section-count .num {
  font-size: var(--text-label);
  color: var(--ink);
}

.panel-note {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

/* 新增文档表单：静态容器，2px 墨边装框不加投影。 */
.form-panel {
  display: grid;
  gap: var(--s3);
  border: var(--line);
  background: var(--panel);
  padding: var(--s4);
  min-width: 0;
}

.document-form,
.upload-form,
.debug-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--s3);
}

.wide {
  grid-column: 1 / -1;
}

.document-form .brut-button,
.upload-form .brut-button,
.debug-form .brut-button[type="submit"] {
  justify-self: start;
}

.upload-form .brut-button.wide {
  justify-self: stretch;
}

.document-form .brut-button.wide {
  justify-self: stretch;
}

/* 与 BrutField 同视觉语言的 selects / textareas / file input。 */
.field-block {
  display: grid;
  gap: var(--s2);
  min-width: 0;
}

.field-block > span {
  color: var(--ink);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1.2;
}

.field-block select,
.field-block textarea,
.field-block input {
  width: 100%;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  font: inherit;
  font-size: var(--text-body);
  line-height: 1.6;
  padding: var(--s3);
}

.field-block textarea {
  resize: vertical;
  min-height: 42px;
}

.field-block select:focus,
.field-block textarea:focus,
.field-block input:focus {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}

.field-block ::placeholder {
  color: var(--ink-soft);
}

/* 文件选择：BrutButton primary 手写等效的 label 按钮 + 视觉隐藏原生 input（保留可聚焦与 change 触发）。 */
.file-picker {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--s3);
  min-width: 0;
}

.file-picker__button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: var(--line);
  border-radius: 0;
  background: var(--action);
  color: var(--action-ink);
  font-family: var(--font-ui);
  font-size: var(--text-strong);
  font-weight: 800;
  line-height: 1.2;
  padding: var(--s3) var(--s4);
  cursor: pointer;
  box-shadow: var(--shadow-2);
  transition: transform 120ms var(--ease-out), box-shadow 120ms var(--ease-out);
}

.file-picker__button:focus-within {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}

.file-picker input[type="file"] {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  border: 0;
  padding: 0;
  background: none;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  overflow: hidden;
  white-space: nowrap;
}

.file-picker__name {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
  overflow-wrap: anywhere;
  min-width: 0;
}

.file-picker__name--set {
  color: var(--ink);
}

@media (hover: hover) and (pointer: fine) {
  .file-picker__button:hover {
    transform: translateY(-1px);
  }
}

.form-error {
  border: var(--line);
  background: var(--danger);
  color: var(--action-ink);
  font-size: var(--text-strong);
  font-weight: 800;
  padding: var(--s3);
}

/* 上传区（BrutPanel 黑头 + 白身）。 */
.upload-panel {
  min-width: 0;
}

.upload-body {
  display: grid;
  gap: var(--s4);
  min-width: 0;
}

.ingestion-result,
.task-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--s2) var(--s3);
  border: var(--line);
  background: var(--paper);
  padding: var(--s3);
}

.ingestion-result strong {
  font-size: var(--text-strong);
  font-weight: 900;
}

.ingestion-result > span {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
}

.ingestion-history {
  display: grid;
  gap: var(--s3);
}

.task-list {
  display: grid;
  gap: var(--s3);
}

.task-row {
  justify-content: space-between;
}

.task-row__main {
  display: grid;
  gap: var(--s1);
  min-width: 0;
}

.task-row__main strong {
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

.task-row__main span {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
}

.task-row__main small {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.num {
  font-family: var(--font-mono);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
}

.task-row__main .num,
.doc-row__data .num,
.section-count .num {
  color: var(--ink);
}

/* 工作区两栏。 */
.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  gap: var(--s5);
  align-items: start;
}

.main-column,
.side-column {
  display: grid;
  gap: var(--s4);
  min-width: 0;
}

.ledger-section {
  display: grid;
  gap: var(--s3);
  min-width: 0;
}

.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--s3);
  border: var(--line);
  background: var(--panel);
  padding: var(--s4);
}

.filter-block {
  display: grid;
  gap: var(--s2);
  min-width: 0;
}

.filter-block > span {
  color: var(--ink);
  font-size: var(--text-label);
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1.2;
}

.filter-block select,
.filter-block input {
  width: 100%;
  border: var(--line);
  border-radius: 0;
  background: var(--panel);
  color: var(--ink);
  font: inherit;
  font-size: var(--text-body);
  padding: var(--s2) var(--s3);
}

.filter-block select:focus,
.filter-block input:focus {
  outline: 2px solid var(--ink);
  outline-offset: 2px;
}

/* T2 文档台账行：2px 墨边装框，无投影；行内交互按钮可带投影。 */
.document-list {
  display: grid;
  gap: var(--s3);
}

.doc-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--s4);
  align-items: start;
  border: var(--line);
  background: var(--panel);
  padding: var(--s4);
}

.doc-row__main {
  display: grid;
  gap: var(--s2);
  min-width: 0;
}

.doc-row__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
  flex-wrap: wrap;
}

.doc-row__head strong {
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

.doc-row__meta,
.doc-row__data {
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

.doc-row__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--s2);
}

.empty {
  border: 2px dashed var(--ink);
  background: var(--panel);
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
  padding: var(--s4);
}

.debug-toggle {
  justify-self: start;
}

/* RAG 调试：命中分组盒 + 命中行。 */
.debug-body {
  display: grid;
  gap: var(--s4);
  min-width: 0;
}

.debug-result {
  display: grid;
  gap: var(--s3);
}

.hit-group {
  display: grid;
  gap: var(--s2);
  border: var(--line);
  background: var(--paper);
  padding: var(--s3);
}

.hit-group h3 {
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.2;
}

.hit-list {
  display: grid;
  gap: var(--s2);
}

.hit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
  border: 1px solid var(--ink);
  background: var(--panel);
  padding: var(--s2) var(--s3);
}

.hit-row > span {
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.raw-debug {
  border: var(--line);
  background: var(--paper);
  padding: var(--s3);
}

summary {
  cursor: pointer;
  font-size: var(--text-body);
  font-weight: 800;
}

pre {
  max-width: 100%;
  margin: var(--s2) 0 0;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--font-mono);
  font-size: var(--text-data);
  line-height: 1.6;
}

/* 文档详情抽屉（BrutPanel）内的 chunk 行。 */
.detail {
  display: grid;
  gap: var(--s3);
  min-width: 0;
}

.detail > strong {
  font-size: var(--text-strong);
  font-weight: 900;
  line-height: 1.3;
  overflow-wrap: anywhere;
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--s1);
  color: var(--ink-soft);
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.6;
}

.chunk-row {
  display: grid;
  gap: var(--s2);
  border: var(--line);
  background: var(--paper);
  padding: var(--s3);
  min-width: 0;
}

.chunk-row__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--s2);
}

.chunk-row__head > span {
  font-family: var(--font-mono);
  font-size: var(--text-label);
  font-weight: 900;
  font-variant-numeric: tabular-nums;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.chunk-row > p {
  font-size: var(--text-body);
  font-weight: 700;
  line-height: 1.7;
}

@media (max-width: 960px) {
  .page-head {
    flex-direction: column;
  }

  .workspace-grid,
  .document-form,
  .upload-form,
  .debug-form {
    grid-template-columns: 1fr;
  }

  .doc-row {
    grid-template-columns: 1fr;
  }

  .doc-row__actions {
    justify-content: flex-start;
  }
}
</style>
