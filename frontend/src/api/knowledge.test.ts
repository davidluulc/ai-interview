import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createRagDocument,
  debugRagContext,
  deleteRagDocument,
  fetchRagDocumentDetail,
  fetchRagDocuments,
  getIngestionTasks,
  getIngestionTask,
  retryIngestionTask,
  updateRagDocumentStatus,
  uploadKnowledgeFile
} from "./knowledge";

describe("knowledge api", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("loads rag documents with an optional knowledge base filter", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ items: [] }));

    await fetchRagDocuments("role_knowledge");

    expect(fetchMock).toHaveBeenCalledWith("/api/rag/documents?knowledgeBase=role_knowledge", expect.any(Object));
  });

  it("creates a rag document with json payload", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ id: 1 }));

    await createRagDocument({
      title: "FastAPI Depends",
      knowledgeBase: "role_knowledge",
      sourceType: "manual",
      content: "Depends 是 FastAPI 的依赖注入机制。",
      visibility: "private",
      metadata: { role: "Python 后端" }
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/rag/documents",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          title: "FastAPI Depends",
          knowledgeBase: "role_knowledge",
          sourceType: "manual",
          content: "Depends 是 FastAPI 的依赖注入机制。",
          visibility: "private",
          metadata: { role: "Python 后端" }
        })
      })
    );
  });

  it("loads document detail, updates status and deletes a document", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() => Promise.resolve(jsonResponse({ ok: true })));

    await fetchRagDocumentDetail(7);
    await updateRagDocumentStatus(7, "disabled");
    await deleteRagDocument(7);

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/rag/documents/7", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/rag/documents/7/status",
      expect.objectContaining({ method: "PATCH", body: JSON.stringify({ status: "disabled" }) })
    );
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/rag/documents/7", expect.objectContaining({ method: "DELETE" }));
  });

  it("builds rag debug query params", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ quality: {} }));

    await debugRagContext({
      candidateName: "David",
      role: "AI 应用开发实习生",
      positionTag: "ai_app",
      resume: "做过 RAG 项目",
      jd: "熟悉 Agent",
      stage: "技术追问"
    });

    const calledPath = String(fetchMock.mock.calls[0][0]);
    expect(calledPath).toContain("/api/rag/debug?");
    expect(calledPath).toContain("name=David");
    expect(calledPath).toContain("role=AI+%E5%BA%94%E7%94%A8%E5%BC%80%E5%8F%91%E5%AE%9E%E4%B9%A0%E7%94%9F");
    expect(calledPath).toContain("stage=%E6%8A%80%E6%9C%AF%E8%BF%BD%E9%97%AE");
  });

  it("uploads a knowledge file with multipart form data", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        taskId: "rag_ingestion-1",
        status: "success",
        document: { id: 12, title: "FastAPI Depends" },
        preview: { textLength: 120, chunkCount: 2, warnings: [] }
      })
    );
    const formData = new FormData();
    formData.append("title", "FastAPI Depends");

    await uploadKnowledgeFile(formData);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/rag/documents/upload",
      expect.objectContaining({
        method: "POST",
        body: formData
      })
    );
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(new Headers(init.headers).has("Content-Type")).toBe(false);
  });

  it("loads a rag ingestion task by id", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ taskId: "rag_ingestion-1" }));

    await getIngestionTask("rag_ingestion-1");

    expect(fetchMock).toHaveBeenCalledWith("/api/rag/documents/ingestion-tasks/rag_ingestion-1", expect.any(Object));
  });

  it("loads and retries rag ingestion tasks", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() => Promise.resolve(jsonResponse({ items: [] })));

    await getIngestionTasks();
    await retryIngestionTask("rag_ingestion-1");

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/rag/documents/ingestion-tasks", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/rag/documents/ingestion-tasks/rag_ingestion-1/retry",
      expect.objectContaining({ method: "POST" })
    );
  });
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" }
  });
}
