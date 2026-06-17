# Vue3 知识库页面产品化 V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Vue3 知识库页从占位页升级为可管理 RAG 文档、查看 chunks、运行 RAG debug 和展示命中解释的产品化工作台。

**Architecture:** 本阶段只改 Vue3 前端和中文学习文档，优先复用现有 FastAPI RAG 接口。API client 负责 HTTP 协议和类型，Pinia store 负责列表、筛选、详情、debug、错误和加载状态，`KnowledgePage.vue` 只负责编排页面和交互。

**Tech Stack:** Vue3、Vite、TypeScript、Pinia、Vue Router、Vitest、@vue/test-utils、现有 FastAPI RAG API。

---

## File Structure

- Create: `frontend/src/api/knowledge.ts`
  - 定义 RAG 文档、chunk、debug 请求和响应类型。
  - 封装 `/api/rag/documents`、`/api/rag/documents/{id}`、`/api/rag/debug`。
- Create: `frontend/src/api/knowledge.test.ts`
  - 先验证请求路径、请求方法、payload 和 query string。
- Create: `frontend/src/stores/knowledge.ts`
  - 管理文档列表、筛选条件、文档详情、debug 结果、加载和错误状态。
- Create: `frontend/src/stores/knowledge.test.ts`
  - 验证加载、筛选、metadata JSON 校验、创建、状态更新、删除和 debug。
- Modify: `frontend/src/pages/app/KnowledgePage.vue`
  - 从占位页升级为知识库工作台。
- Create: `frontend/src/pages/app/knowledge-page.test.ts`
  - 验证页面渲染、筛选控件、表单校验、详情 chunks 和 debug 结果。
- Create: `docs/learning/16-Vue3知识库页面如何承接RAG工程能力.md`
  - 用中文解释 API 层、store 层、页面层如何承接 RAG 工程能力。

## Task 1: Knowledge API Client

**Files:**
- Create: `frontend/src/api/knowledge.test.ts`
- Create: `frontend/src/api/knowledge.ts`

- [ ] **Step 1: Write the failing API tests**

Create `frontend/src/api/knowledge.test.ts` with tests covering:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createRagDocument,
  debugRagContext,
  deleteRagDocument,
  fetchRagDocumentDetail,
  fetchRagDocuments,
  updateRagDocumentStatus
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
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ ok: true }));
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
});

function jsonResponse(body: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    })
  );
}
```

- [ ] **Step 2: Run API test to verify RED**

Run:

```powershell
cd frontend
npm.cmd run test -- src/api/knowledge.test.ts
```

Expected: FAIL because `./knowledge` does not exist.

- [ ] **Step 3: Implement API client**

Create `frontend/src/api/knowledge.ts` with:

```ts
import { apiRequest } from "./client";

export type KnowledgeBaseType = "role_knowledge" | "question_bank" | "candidate_memory";
export type RagDocumentStatus = "enabled" | "disabled" | "archived";
export type RagDocumentVisibility = "private" | "public";

export interface RagDocument {
  id: number;
  title: string;
  knowledgeBase: KnowledgeBaseType | string;
  sourceType?: string;
  status: RagDocumentStatus | string;
  visibility: RagDocumentVisibility | string;
  content?: string;
  metadata?: Record<string, unknown>;
  chunkCount?: number;
  duplicateChunkCount?: number;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface RagChunk {
  id: number;
  documentId: number;
  title?: string;
  content: string;
  chunkIndex: number;
  chunkHash?: string;
  isDuplicate?: boolean;
  keywords?: string[];
  metadata?: Record<string, unknown>;
  embeddingStatus?: string;
  embeddingModel?: string;
  embeddingSize?: number;
}

export interface RagDocumentListResponse {
  items: RagDocument[];
}

export interface RagDocumentDetailResponse {
  document: RagDocument;
  chunks: RagChunk[];
}

export interface CreateRagDocumentPayload {
  title: string;
  knowledgeBase: KnowledgeBaseType;
  sourceType: string;
  content: string;
  visibility: RagDocumentVisibility;
  metadata: Record<string, unknown>;
}

export interface RagDebugPayload {
  candidateName?: string;
  role?: string;
  positionTag?: string;
  resume?: string;
  jd?: string;
  stage?: string;
}

export interface RagDebugResult {
  roleKnowledge?: unknown[];
  questionBank?: unknown[];
  candidateMemory?: unknown[];
  quality?: Record<string, unknown>;
  explanations?: Record<string, unknown>;
}

export function fetchRagDocuments(knowledgeBase = ""): Promise<RagDocumentListResponse> {
  const query = knowledgeBase ? `?knowledgeBase=${encodeURIComponent(knowledgeBase)}` : "";
  return apiRequest<RagDocumentListResponse>(`/api/rag/documents${query}`);
}

export function createRagDocument(payload: CreateRagDocumentPayload): Promise<RagDocument> {
  return apiRequest<RagDocument>("/api/rag/documents", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function fetchRagDocumentDetail(documentId: number): Promise<RagDocumentDetailResponse> {
  return apiRequest<RagDocumentDetailResponse>(`/api/rag/documents/${documentId}`);
}

export function updateRagDocumentStatus(documentId: number, status: RagDocumentStatus): Promise<RagDocument> {
  return apiRequest<RagDocument>(`/api/rag/documents/${documentId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status })
  });
}

export function deleteRagDocument(documentId: number): Promise<{ ok: boolean }> {
  return apiRequest<{ ok: boolean }>(`/api/rag/documents/${documentId}`, { method: "DELETE" });
}

export function debugRagContext(payload: RagDebugPayload): Promise<RagDebugResult> {
  const params = new URLSearchParams({
    name: payload.candidateName || "",
    role: payload.role || "",
    positionTag: payload.positionTag || "",
    resume: payload.resume || "",
    jd: payload.jd || "",
    stage: payload.stage || ""
  });
  return apiRequest<RagDebugResult>(`/api/rag/debug?${params.toString()}`);
}
```

- [ ] **Step 4: Run API test to verify GREEN**

Run:

```powershell
cd frontend
npm.cmd run test -- src/api/knowledge.test.ts
```

Expected: PASS.

## Task 2: Knowledge Store

**Files:**
- Create: `frontend/src/stores/knowledge.test.ts`
- Create: `frontend/src/stores/knowledge.ts`

- [ ] **Step 1: Write failing store tests**

Create tests for:

- loading documents into `documents`
- filtering by knowledge base, status, visibility and title search
- rejecting invalid metadata JSON with readable error
- creating a document and refreshing list
- loading detail and storing chunks
- updating status
- deleting document
- running debug and storing result

Use `vi.mock("@/api/knowledge", ...)` following the style of `frontend/src/stores/history.test.ts`.

- [ ] **Step 2: Run store test to verify RED**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/knowledge.test.ts
```

Expected: FAIL because store does not exist.

- [ ] **Step 3: Implement store**

Create `frontend/src/stores/knowledge.ts` with:

- `documents`
- `selectedDetail`
- `debugResult`
- `loading`
- `saving`
- `debugLoading`
- `error`
- `metadataError`
- filters: `knowledgeBaseFilter`, `statusFilter`, `visibilityFilter`, `searchKeyword`
- computed `filteredDocuments`
- actions: `loadDocuments`, `createDocumentFromForm`, `loadDocumentDetail`, `updateStatus`, `removeDocument`, `runDebug`, `setFilters`

Metadata JSON parser must return:

```text
metadata 必须是合法 JSON 对象，例如 {"role":"Python 后端","level":"实习"}。
```

when parsing fails or parsed value is not an object.

- [ ] **Step 4: Run store test to verify GREEN**

Run:

```powershell
cd frontend
npm.cmd run test -- src/stores/knowledge.test.ts
```

Expected: PASS.

## Task 3: Knowledge Page

**Files:**
- Create: `frontend/src/pages/app/knowledge-page.test.ts`
- Modify: `frontend/src/pages/app/KnowledgePage.vue`

- [ ] **Step 1: Write failing page tests**

Create tests covering:

- renders title, counts and document cards
- updates filters from controls
- toggles create form and shows metadata JSON error
- opens document detail and renders chunk content
- triggers status actions and delete confirmation
- renders RAG debug result with three hit groups

Mock `@/stores/knowledge` and stub `AppLayout`, following existing page test style.

- [ ] **Step 2: Run page test to verify RED**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/knowledge-page.test.ts
```

Expected: FAIL because `KnowledgePage.vue` is still an occupied placeholder.

- [ ] **Step 3: Implement KnowledgePage**

Replace placeholder content with:

- page header and add document button
- metric chips for total/enabled/archived
- filter controls with `data-testid`
- document list with actions
- create document form
- detail panel with chunks
- RAG debug panel
- responsive CSS without horizontal overflow

- [ ] **Step 4: Run page test to verify GREEN**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/knowledge-page.test.ts
```

Expected: PASS.

## Task 4: Learning Document

**Files:**
- Create: `docs/learning/16-Vue3知识库页面如何承接RAG工程能力.md`

- [ ] **Step 1: Create learning document**

Document these points in Chinese:

- 为什么知识库页面不是重新做 RAG
- API client / Pinia store / Vue page 各自负责什么
- 三类知识库如何对应面试系统
- status / visibility / metadata / chunk 为什么是 RAG 工程化关键词
- 面试时怎么讲这一阶段

- [ ] **Step 2: Review for clarity**

Run:

```powershell
Get-Content -Raw -Encoding UTF8 docs\learning\16-Vue3知识库页面如何承接RAG工程能力.md
```

Expected: no broken headings, no placeholder words.

## Task 5: Full Verification

**Files:**
- All files above.

- [ ] **Step 1: Run focused frontend tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/api/knowledge.test.ts src/stores/knowledge.test.ts src/pages/app/knowledge-page.test.ts
```

Expected: PASS.

- [ ] **Step 2: Run all frontend tests**

Run:

```powershell
cd frontend
npm.cmd run test
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```powershell
cd frontend
npm.cmd run build
```

Expected: PASS.

- [ ] **Step 4: Browser verification**

Open:

```text
http://127.0.0.1:5173/vue/app/knowledge
```

Verify:

- desktop layout renders document management and debug panels
- mobile width around 390px has no horizontal overflow
- no visible `undefined`
- create form, filters, detail and debug sections are reachable

## Self-Review

- Spec coverage: plan covers API, store, page, testing, browser verification and learning document.
- Scope control: plan does not change RAG algorithms, Agent, LangGraph, Docker, Nginx or deployment.
- Placeholder scan: no implementation step relies on vague “do appropriate thing” wording; each task has target files and verification commands.
- Type consistency: knowledge base/status/visibility names match the existing backend API and spec.
