import { defineStore } from "pinia";
import { computed, ref } from "vue";
import * as knowledgeApi from "@/api/knowledge";

export type KnowledgeBaseFilter = knowledgeApi.KnowledgeBaseType | "all";
export type DocumentStatusFilter = knowledgeApi.RagDocumentStatus | "all";
export type DocumentVisibilityFilter = knowledgeApi.RagDocumentVisibility | "all";

export interface KnowledgeFilters {
  knowledgeBase?: KnowledgeBaseFilter;
  status?: DocumentStatusFilter;
  visibility?: DocumentVisibilityFilter;
  searchKeyword?: string;
}

export interface KnowledgeDocumentForm {
  title: string;
  knowledgeBase: knowledgeApi.KnowledgeBaseType;
  sourceType: string;
  content: string;
  visibility: knowledgeApi.RagDocumentVisibility;
  metadataJson: string;
}

export interface KnowledgeUploadForm {
  title: string;
  knowledgeBase: knowledgeApi.KnowledgeBaseType;
  visibility: knowledgeApi.RagDocumentVisibility;
  metadataJson: string;
  file: File | null;
}

const METADATA_ERROR = 'metadata 必须是合法 JSON 对象，例如 {"role":"Python 后端","level":"实习"}。';

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function replaceDocument(
  documents: knowledgeApi.RagDocument[],
  updated: knowledgeApi.RagDocument
): knowledgeApi.RagDocument[] {
  return documents.map((document) => (document.id === updated.id ? updated : document));
}

export const useKnowledgeStore = defineStore("knowledge", () => {
  const documents = ref<knowledgeApi.RagDocument[]>([]);
  const selectedDetail = ref<knowledgeApi.RagDocumentDetailResponse | null>(null);
  const debugResult = ref<knowledgeApi.RagDebugResult | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const debugLoading = ref(false);
  const uploading = ref(false);
  const error = ref("");
  const uploadError = ref("");
  const metadataError = ref("");
  const ingestionTask = ref<knowledgeApi.RagIngestionTask | null>(null);
  const ingestionTasks = ref<knowledgeApi.RagIngestionTask[]>([]);
  const ingestionTasksLoading = ref(false);
  const retryingTaskId = ref("");
  const knowledgeBaseFilter = ref<KnowledgeBaseFilter>("all");
  const statusFilter = ref<DocumentStatusFilter>("all");
  const visibilityFilter = ref<DocumentVisibilityFilter>("all");
  const searchKeyword = ref("");

  const filteredDocuments = computed(() => {
    const keyword = searchKeyword.value.trim().toLowerCase();
    return documents.value.filter((document) => {
      const matchesKnowledgeBase =
        knowledgeBaseFilter.value === "all" || document.knowledgeBase === knowledgeBaseFilter.value;
      const matchesStatus = statusFilter.value === "all" || document.status === statusFilter.value;
      const matchesVisibility = visibilityFilter.value === "all" || document.visibility === visibilityFilter.value;
      const matchesKeyword = !keyword || document.title.toLowerCase().includes(keyword);
      return matchesKnowledgeBase && matchesStatus && matchesVisibility && matchesKeyword;
    });
  });

  const enabledCount = computed(() => documents.value.filter((document) => document.status === "enabled").length);
  const archivedCount = computed(() => documents.value.filter((document) => document.status === "archived").length);

  async function loadDocuments(): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      const result = await knowledgeApi.fetchRagDocuments();
      documents.value = result.items;
    } catch (err) {
      documents.value = [];
      error.value = err instanceof Error ? err.message : "知识库文档加载失败";
    } finally {
      loading.value = false;
    }
  }

  function parseMetadataJson(value: string): Record<string, unknown> | null {
    metadataError.value = "";
    if (!value.trim()) {
      return {};
    }
    try {
      const parsed = JSON.parse(value) as unknown;
      if (!isPlainObject(parsed)) {
        metadataError.value = METADATA_ERROR;
        return null;
      }
      return parsed;
    } catch {
      metadataError.value = METADATA_ERROR;
      return null;
    }
  }

  async function createDocumentFromForm(form: KnowledgeDocumentForm): Promise<boolean> {
    const metadata = parseMetadataJson(form.metadataJson);
    if (!metadata) {
      return false;
    }

    saving.value = true;
    error.value = "";
    try {
      await knowledgeApi.createRagDocument({
        title: form.title,
        knowledgeBase: form.knowledgeBase,
        sourceType: form.sourceType || "manual",
        content: form.content,
        visibility: form.visibility,
        metadata
      });
      await loadDocuments();
      return true;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "知识库文档创建失败";
      return false;
    } finally {
      saving.value = false;
    }
  }

  async function uploadFile(form: KnowledgeUploadForm): Promise<boolean> {
    metadataError.value = "";
    uploadError.value = "";
    if (!form.file) {
      uploadError.value = "请选择要导入的文件";
      return false;
    }

    const metadata = parseMetadataJson(form.metadataJson);
    if (!metadata) {
      return false;
    }

    uploading.value = true;
    try {
      const formData = new FormData();
      formData.append("title", form.title);
      formData.append("knowledgeBase", form.knowledgeBase);
      formData.append("visibility", form.visibility);
      formData.append("metadata", JSON.stringify(metadata));
      formData.append("file", form.file);

      const result = await knowledgeApi.uploadKnowledgeFile(formData);
      ingestionTask.value = result;
      await loadIngestionTasks();
      const document = result.document || result.result?.document;
      if (document) {
        documents.value = [document, ...documents.value.filter((item) => item.id !== document.id)];
      }
      return true;
    } catch (err) {
      uploadError.value = err instanceof Error ? err.message : "文件导入失败";
      return false;
    } finally {
      uploading.value = false;
    }
  }

  async function loadIngestionTasks(): Promise<void> {
    ingestionTasksLoading.value = true;
    try {
      const result = await knowledgeApi.getIngestionTasks();
      ingestionTasks.value = result.items;
    } catch (err) {
      uploadError.value = err instanceof Error ? err.message : "导入任务加载失败";
      ingestionTasks.value = [];
    } finally {
      ingestionTasksLoading.value = false;
    }
  }

  async function retryTask(taskId: string): Promise<void> {
    retryingTaskId.value = taskId;
    uploadError.value = "";
    try {
      ingestionTask.value = await knowledgeApi.retryIngestionTask(taskId);
      await Promise.all([loadIngestionTasks(), loadDocuments()]);
    } catch (err) {
      uploadError.value = err instanceof Error ? err.message : "摄取任务重试失败";
    } finally {
      retryingTaskId.value = "";
    }
  }

  async function loadDocumentDetail(documentId: number): Promise<void> {
    loading.value = true;
    error.value = "";
    try {
      selectedDetail.value = await knowledgeApi.fetchRagDocumentDetail(documentId);
    } catch (err) {
      error.value = err instanceof Error ? err.message : "知识库文档详情加载失败";
    } finally {
      loading.value = false;
    }
  }

  async function updateStatus(documentId: number, status: knowledgeApi.RagDocumentStatus): Promise<void> {
    const updated = await knowledgeApi.updateRagDocumentStatus(documentId, status);
    documents.value = replaceDocument(documents.value, updated);
    if (selectedDetail.value?.document.id === documentId) {
      selectedDetail.value = { ...selectedDetail.value, document: updated };
    }
  }

  async function removeDocument(documentId: number): Promise<void> {
    await knowledgeApi.deleteRagDocument(documentId);
    documents.value = documents.value.filter((document) => document.id !== documentId);
    if (selectedDetail.value?.document.id === documentId) {
      selectedDetail.value = null;
    }
  }

  async function runDebug(payload: knowledgeApi.RagDebugPayload): Promise<void> {
    debugLoading.value = true;
    error.value = "";
    try {
      debugResult.value = await knowledgeApi.debugRagContext(payload);
    } catch (err) {
      error.value = err instanceof Error ? err.message : "RAG 调试失败";
    } finally {
      debugLoading.value = false;
    }
  }

  function setFilters(filters: KnowledgeFilters): void {
    knowledgeBaseFilter.value = filters.knowledgeBase || "all";
    statusFilter.value = filters.status || "all";
    visibilityFilter.value = filters.visibility || "all";
    searchKeyword.value = filters.searchKeyword || "";
  }

  return {
    documents,
    selectedDetail,
    debugResult,
    loading,
    saving,
    debugLoading,
    uploading,
    error,
    uploadError,
    metadataError,
    ingestionTask,
    ingestionTasks,
    ingestionTasksLoading,
    retryingTaskId,
    knowledgeBaseFilter,
    statusFilter,
    visibilityFilter,
    searchKeyword,
    filteredDocuments,
    enabledCount,
    archivedCount,
    loadDocuments,
    createDocumentFromForm,
    uploadFile,
    loadIngestionTasks,
    retryTask,
    loadDocumentDetail,
    updateStatus,
    removeDocument,
    runDebug,
    setFilters
  };
});
