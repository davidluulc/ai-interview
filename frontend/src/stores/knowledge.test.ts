import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as knowledgeApi from "@/api/knowledge";
import { useKnowledgeStore } from "./knowledge";

vi.mock("@/api/knowledge", () => ({
  createRagDocument: vi.fn(),
  debugRagContext: vi.fn(),
  deleteRagDocument: vi.fn(),
  fetchRagDocumentDetail: vi.fn(),
  fetchRagDocuments: vi.fn(),
  getIngestionTask: vi.fn(),
  updateRagDocumentStatus: vi.fn(),
  uploadKnowledgeFile: vi.fn()
}));

describe("knowledge store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(knowledgeApi.createRagDocument).mockReset();
    vi.mocked(knowledgeApi.debugRagContext).mockReset();
    vi.mocked(knowledgeApi.deleteRagDocument).mockReset();
    vi.mocked(knowledgeApi.fetchRagDocumentDetail).mockReset();
    vi.mocked(knowledgeApi.fetchRagDocuments).mockReset();
    vi.mocked(knowledgeApi.getIngestionTask).mockReset();
    vi.mocked(knowledgeApi.updateRagDocumentStatus).mockReset();
    vi.mocked(knowledgeApi.uploadKnowledgeFile).mockReset();
  });

  it("loads documents and filters them for the current knowledge workspace", async () => {
    vi.mocked(knowledgeApi.fetchRagDocuments).mockResolvedValue({
      items: [
        documentFixture({ id: 1, title: "FastAPI Depends", knowledgeBase: "role_knowledge", status: "enabled" }),
        documentFixture({ id: 2, title: "RAG 题库", knowledgeBase: "question_bank", status: "disabled" }),
        documentFixture({ id: 3, title: "候选人画像", knowledgeBase: "candidate_memory", visibility: "public" })
      ]
    });

    const store = useKnowledgeStore();
    await store.loadDocuments();

    expect(store.documents).toHaveLength(3);
    expect(store.enabledCount).toBe(2);
    expect(store.archivedCount).toBe(0);

    store.setFilters({
      knowledgeBase: "role_knowledge",
      status: "enabled",
      visibility: "all",
      searchKeyword: "depends"
    });

    expect(store.filteredDocuments.map((item) => item.id)).toEqual([1]);
  });

  it("records a readable error when document loading fails", async () => {
    vi.mocked(knowledgeApi.fetchRagDocuments).mockRejectedValue(new Error("登录已过期"));

    const store = useKnowledgeStore();
    await store.loadDocuments();

    expect(store.documents).toEqual([]);
    expect(store.error).toBe("登录已过期");
    expect(store.loading).toBe(false);
  });

  it("rejects invalid metadata json before creating a document", async () => {
    const store = useKnowledgeStore();

    const created = await store.createDocumentFromForm({
      title: "FastAPI Depends",
      knowledgeBase: "role_knowledge",
      sourceType: "manual",
      content: "Depends 是依赖注入。",
      visibility: "private",
      metadataJson: "{bad json"
    });

    expect(created).toBe(false);
    expect(store.metadataError).toContain("metadata 必须是合法 JSON 对象");
    expect(knowledgeApi.createRagDocument).not.toHaveBeenCalled();
  });

  it("creates a document and refreshes the list after metadata validation passes", async () => {
    vi.mocked(knowledgeApi.createRagDocument).mockResolvedValue(documentFixture({ id: 9, title: "新增文档" }));
    vi.mocked(knowledgeApi.fetchRagDocuments).mockResolvedValue({ items: [documentFixture({ id: 9, title: "新增文档" })] });

    const store = useKnowledgeStore();
    const created = await store.createDocumentFromForm({
      title: "新增文档",
      knowledgeBase: "question_bank",
      sourceType: "manual",
      content: "请解释 RAG 的召回链路。",
      visibility: "private",
      metadataJson: '{"difficulty":"medium"}'
    });

    expect(created).toBe(true);
    expect(knowledgeApi.createRagDocument).toHaveBeenCalledWith({
      title: "新增文档",
      knowledgeBase: "question_bank",
      sourceType: "manual",
      content: "请解释 RAG 的召回链路。",
      visibility: "private",
      metadata: { difficulty: "medium" }
    });
    expect(store.documents).toHaveLength(1);
  });

  it("uploads a file and inserts the created document into the list", async () => {
    vi.mocked(knowledgeApi.uploadKnowledgeFile).mockResolvedValue({
      taskId: "rag_ingestion-1",
      status: "success",
      document: documentFixture({ id: 10, title: "FastAPI 文件导入", sourceType: "upload" }),
      preview: { textLength: 128, chunkCount: 2, warnings: [] }
    });

    const store = useKnowledgeStore();
    store.documents = [documentFixture({ id: 1, title: "已有文档" })];
    const file = new File(["FastAPI Depends"], "depends.txt", { type: "text/plain" });

    const result = await store.uploadFile({
      title: "FastAPI 文件导入",
      knowledgeBase: "role_knowledge",
      visibility: "private",
      metadataJson: '{"positionTag":"python_backend"}',
      file
    });

    expect(result).toBe(true);
    expect(knowledgeApi.uploadKnowledgeFile).toHaveBeenCalledWith(expect.any(FormData));
    expect(store.ingestionTask?.status).toBe("success");
    expect(store.documents.map((item) => item.title)).toEqual(["FastAPI 文件导入", "已有文档"]);
    expect(store.uploading).toBe(false);
  });

  it("records upload errors and rejects invalid upload metadata", async () => {
    const store = useKnowledgeStore();
    const file = new File(["RAG"], "rag.txt", { type: "text/plain" });

    const invalid = await store.uploadFile({
      title: "RAG",
      knowledgeBase: "role_knowledge",
      visibility: "private",
      metadataJson: "[]",
      file
    });

    expect(invalid).toBe(false);
    expect(store.metadataError).toContain("metadata 必须是合法 JSON 对象");
    expect(knowledgeApi.uploadKnowledgeFile).not.toHaveBeenCalled();

    vi.mocked(knowledgeApi.uploadKnowledgeFile).mockRejectedValue(new Error("Unsupported file type"));
    const failed = await store.uploadFile({
      title: "RAG",
      knowledgeBase: "role_knowledge",
      visibility: "private",
      metadataJson: "{}",
      file
    });

    expect(failed).toBe(false);
    expect(store.uploadError).toBe("Unsupported file type");
    expect(store.uploading).toBe(false);
  });

  it("loads detail, updates status, deletes documents and runs debug", async () => {
    vi.mocked(knowledgeApi.fetchRagDocumentDetail).mockResolvedValue({
      document: documentFixture({ id: 4, title: "详情文档" }),
      chunks: [
        {
          id: 11,
          documentId: 4,
          content: "Depends 会把依赖函数的返回值注入接口。",
          chunkIndex: 0,
          chunkHash: "hash-1"
        }
      ]
    });
    vi.mocked(knowledgeApi.updateRagDocumentStatus).mockResolvedValue(
      documentFixture({ id: 4, title: "详情文档", status: "archived" })
    );
    vi.mocked(knowledgeApi.deleteRagDocument).mockResolvedValue({ ok: true });
    vi.mocked(knowledgeApi.debugRagContext).mockResolvedValue({
      roleKnowledge: [{ title: "岗位知识" }],
      questionBank: [{ title: "题库" }],
      candidateMemory: [{ title: "候选人画像" }],
      quality: { roleKnowledge: { level: "good" } },
      explanations: { roleKnowledge: { summary: "命中岗位资料" } }
    });

    const store = useKnowledgeStore();
    store.documents = [documentFixture({ id: 4, title: "详情文档" })];

    await store.loadDocumentDetail(4);
    expect(store.selectedDetail?.chunks[0].content).toContain("Depends");

    await store.updateStatus(4, "archived");
    expect(store.documents[0].status).toBe("archived");

    await store.runDebug({ role: "Python 后端", stage: "技术基础" });
    expect(store.debugResult?.roleKnowledge).toHaveLength(1);

    await store.removeDocument(4);
    expect(store.documents).toEqual([]);
  });
});

function documentFixture(overrides: Partial<knowledgeApi.RagDocument> = {}): knowledgeApi.RagDocument {
  return {
    id: 1,
    title: "示例文档",
    knowledgeBase: "role_knowledge",
    sourceType: "manual",
    status: "enabled",
    visibility: "private",
    chunkCount: 2,
    duplicateChunkCount: 0,
    updatedAt: "2026-06-13T10:00:00",
    metadata: {},
    ...overrides
  };
}
