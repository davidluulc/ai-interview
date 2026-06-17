# RAG Document Ingestion V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-style RAG document ingestion path so users can upload knowledge files, parse text, track ingestion status, and reuse the existing RAG document/chunk pipeline.

**Architecture:** Add a focused backend ingestion service, extend the existing RAG document route with upload and task-status endpoints, then connect the Vue3 knowledge page to the upload flow. Keep retrieval, hybrid search, rerank, Agent, LangGraph, Docker, and deployment unchanged.

**Tech Stack:** FastAPI, SQLAlchemy, existing `task_status.py`, existing `rag_store.py`, Vue3, Pinia, Vitest, pytest.

---

## File Map

- Create: `backend_python/rag_ingestion.py`
  - File validation, text extraction, cleaning, preview generation.
- Modify: `backend_python/routes/rag_documents.py`
  - Add upload endpoint and ingestion task lookup endpoint.
- Create: `tests/test_rag_document_ingestion.py`
  - Unit tests for parsing, cleaning, validation, and preview.
- Create: `tests/test_rag_documents_upload_route.py`
  - Route tests for upload success/failure and task status.
- Modify: `frontend/src/api/knowledge.ts`
  - Add upload and ingestion task APIs.
- Modify: `frontend/src/stores/knowledge.ts`
  - Add upload state, task result, and error handling.
- Modify: `frontend/src/pages/app/KnowledgePage.vue`
  - Add file import panel.
- Modify: `frontend/src/api/knowledge.test.ts`
  - API request tests.
- Modify: `frontend/src/stores/knowledge.test.ts`
  - Store behavior tests.
- Modify: `frontend/src/pages/app/knowledge-page.test.ts`
  - UI tests for upload panel.
- Create: `docs/learning/20-RAG文档摄取链路如何从文件到chunk.md`
  - Chinese learning document.
- Modify: `docs/roadmap/current-state.md`
  - Update current active stage and final completion.
- Modify: `docs/specs/README.md`
  - Point to active/completed spec.
- Modify: `docs/plans/README.md`
  - Point to active/completed plan.

---

## Task 1: Backend Ingestion Service

**Files:**
- Create: `backend_python/rag_ingestion.py`
- Test: `tests/test_rag_document_ingestion.py`

- [ ] **Step 1: Write failing unit tests**

Create `tests/test_rag_document_ingestion.py`:

```python
import pytest

from backend_python.rag_ingestion import (
    IngestionError,
    build_ingestion_preview,
    clean_extracted_text,
    extract_text_from_upload,
    validate_upload_filename,
)


def test_validate_upload_filename_accepts_text_markdown_and_pdf():
    assert validate_upload_filename("role.md") == ".md"
    assert validate_upload_filename("notes.txt") == ".txt"
    assert validate_upload_filename("resume.pdf") == ".pdf"


def test_validate_upload_filename_rejects_unknown_type():
    with pytest.raises(IngestionError) as exc:
        validate_upload_filename("table.xlsx")
    assert "Unsupported file type" in str(exc.value)


def test_clean_extracted_text_normalizes_blank_lines_and_spaces():
    raw = "  FastAPI   Depends\\r\\n\\r\\n\\r\\nRAG\\tchunk  "
    assert clean_extracted_text(raw) == "FastAPI Depends\\n\\nRAG chunk"


def test_build_ingestion_preview_returns_text_and_chunk_stats():
    preview = build_ingestion_preview("第一段内容\\n\\n第二段内容", title="测试文档")
    assert preview["title"] == "测试文档"
    assert preview["textLength"] > 0
    assert preview["chunkCount"] == 2
    assert preview["warnings"] == []


def test_build_ingestion_preview_rejects_empty_text():
    with pytest.raises(IngestionError) as exc:
        build_ingestion_preview("   ", title="空文档")
    assert "empty text" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_extract_text_from_txt_upload():
    text = await extract_text_from_upload(filename="sample.txt", content=b"hello rag")
    assert text == "hello rag"
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_rag_document_ingestion.py -q
```

Expected:

```text
ModuleNotFoundError or ImportError for backend_python.rag_ingestion
```

- [ ] **Step 3: Implement minimal ingestion service**

Create `backend_python/rag_ingestion.py`:

```python
import re
from pathlib import Path
from typing import Any

from .rag_store import split_content_into_chunks

SUPPORTED_UPLOAD_EXTENSIONS = {".txt", ".md", ".pdf"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class IngestionError(ValueError):
    pass


def validate_upload_filename(filename: str) -> str:
    extension = Path(str(filename or "")).suffix.lower()
    if extension not in SUPPORTED_UPLOAD_EXTENSIONS:
        raise IngestionError(f"Unsupported file type: {extension or 'unknown'}")
    return extension


def validate_upload_size(content: bytes, max_bytes: int = MAX_UPLOAD_BYTES) -> None:
    if not content:
        raise IngestionError("Uploaded file is empty.")
    if len(content) > max_bytes:
        raise IngestionError(f"Uploaded file is too large. Max size is {max_bytes} bytes.")


def clean_extracted_text(text: str) -> str:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    lines = [line.strip() for line in normalized.split("\n")]
    return "\n".join(lines).strip()


def decode_text_bytes(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IngestionError("Only UTF-8 text files are supported in this version.") from exc


def extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise IngestionError("PDF parsing dependency is unavailable. Install pypdf to parse PDF files.") from exc

    try:
        import io

        reader = PdfReader(io.BytesIO(content))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise IngestionError("Failed to parse PDF file.") from exc


async def extract_text_from_upload(*, filename: str, content: bytes) -> str:
    extension = validate_upload_filename(filename)
    validate_upload_size(content)
    if extension in {".txt", ".md"}:
        return clean_extracted_text(decode_text_bytes(content))
    if extension == ".pdf":
        return clean_extracted_text(extract_pdf_text(content))
    raise IngestionError(f"Unsupported file type: {extension}")


def build_ingestion_preview(text: str, *, title: str) -> dict[str, Any]:
    cleaned = clean_extracted_text(text)
    if not cleaned:
        raise IngestionError("Parsed empty text from uploaded file.")
    chunks = split_content_into_chunks(cleaned)
    if not chunks:
        raise IngestionError("No chunks generated from uploaded file.")
    warnings: list[str] = []
    if len(cleaned) < 80:
        warnings.append("文本较短，可能无法形成高质量 RAG 召回。")
    return {
        "title": title.strip(),
        "textLength": len(cleaned),
        "chunkCount": len(chunks),
        "warnings": warnings,
    }
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```powershell
python -m pytest tests/test_rag_document_ingestion.py -q
```

Expected:

```text
6 passed
```

---

## Task 2: Upload Route And Task Status

**Files:**
- Modify: `backend_python/routes/rag_documents.py`
- Test: `tests/test_rag_documents_upload_route.py`

- [ ] **Step 1: Write failing route tests**

Create `tests/test_rag_documents_upload_route.py` using the existing auth test helpers in the repo. If helper names differ, inspect `tests/test_rag_document_lifecycle.py` and follow its login pattern.

Test cases:

```python
def test_upload_text_document_creates_rag_document(client, auth_headers):
    response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers,
        data={
            "title": "FastAPI Depends 资料",
            "knowledgeBase": "role",
            "visibility": "private",
            "metadata": '{"positionTag":"python_backend"}',
        },
        files={"file": ("depends.txt", b"FastAPI Depends is dependency injection.\\n\\nRAG chunk metadata.", "text/plain")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["document"]["title"] == "FastAPI Depends 资料"
    assert body["preview"]["chunkCount"] >= 1
    assert body["taskId"].startswith("rag_ingestion-")


def test_upload_rejects_unsupported_file_type(client, auth_headers):
    response = client.post(
        "/api/rag/documents/upload",
        headers=auth_headers,
        data={"title": "表格", "knowledgeBase": "role", "visibility": "private"},
        files={"file": ("bad.xlsx", b"not supported", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
```

- [ ] **Step 2: Run route tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_rag_documents_upload_route.py -q
```

Expected:

```text
404 Not Found for /api/rag/documents/upload
```

- [ ] **Step 3: Implement upload route**

Modify `backend_python/routes/rag_documents.py`:

```python
import json

from fastapi import File, Form, UploadFile

from ..rag_ingestion import IngestionError, build_ingestion_preview, extract_text_from_upload
from ..task_status import create_task_status, fail_task_status, get_task_status, succeed_task_status, update_task_status
```

Add route before `@router.get("/{document_id}")`:

```python
@router.post("/upload")
async def upload_document(
    title: str = Form(...),
    knowledgeBase: str = Form(...),
    visibility: str = Form("private"),
    metadata: str = Form("{}"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    task = create_task_status(task_type="rag_ingestion", message="RAG document ingestion task created.")
    task_id = task["taskId"]
    try:
        update_task_status(task_id, status="running", progress=20, message="Parsing uploaded file.")
        content = await file.read()
        text = await extract_text_from_upload(filename=file.filename or title, content=content)
        preview = build_ingestion_preview(text, title=title)
        update_task_status(task_id, status="running", progress=60, message="Creating RAG document.")
        parsed_metadata = json.loads(metadata or "{}")
        if not isinstance(parsed_metadata, dict):
            raise IngestionError("metadata must be a JSON object.")
        document = await create_rag_document_with_embeddings(
            db,
            user_id=current_user.id,
            title=title,
            knowledge_base=validate_knowledge_base(knowledgeBase),
            source_type="upload",
            content=text,
            metadata={
                **parsed_metadata,
                "originalFilename": file.filename or "",
                "ingestionTaskId": task_id,
            },
            visibility=normalize_document_visibility(visibility),
        )
        result = {"document": serialize_document(document), "preview": preview}
        succeed_task_status(task_id, result=result, message="RAG document ingestion finished.")
        return {"taskId": task_id, "status": "success", **result}
    except (IngestionError, json.JSONDecodeError) as exc:
        fail_task_status(task_id, error=str(exc), message="RAG document ingestion failed.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
```

Add task lookup:

```python
@router.get("/ingestion-tasks/{task_id}")
async def get_ingestion_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    task = get_task_status(task_id)
    if not task or task.get("taskType") != "rag_ingestion":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG ingestion task not found")
    return task
```

- [ ] **Step 4: Run focused backend tests**

Run:

```powershell
python -m pytest tests/test_rag_document_ingestion.py tests/test_rag_documents_upload_route.py -q
```

Expected:

```text
All focused ingestion tests pass.
```

---

## Task 3: Vue3 API And Store

**Files:**
- Modify: `frontend/src/api/knowledge.ts`
- Modify: `frontend/src/stores/knowledge.ts`
- Test: `frontend/src/api/knowledge.test.ts`
- Test: `frontend/src/stores/knowledge.test.ts`

- [ ] **Step 1: Add failing API/store tests**

In `frontend/src/api/knowledge.test.ts`, add a test that verifies:

```ts
await uploadKnowledgeFile(formData)
expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/rag/documents/upload'), expect.objectContaining({
  method: 'POST',
  body: formData,
}))
```

In `frontend/src/stores/knowledge.test.ts`, add a test that verifies successful upload stores:

```ts
expect(store.ingestionTask?.status).toBe('success')
expect(store.documents[0].title).toContain('FastAPI')
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
cd frontend
npm.cmd run test -- src/api/knowledge.test.ts src/stores/knowledge.test.ts
```

Expected:

```text
uploadKnowledgeFile or store.uploadKnowledgeFile is not defined.
```

- [ ] **Step 3: Implement API and store**

Add to `frontend/src/api/knowledge.ts`:

```ts
export async function uploadKnowledgeFile(formData: FormData) {
  return request('/api/rag/documents/upload', {
    method: 'POST',
    body: formData,
  })
}

export async function getIngestionTask(taskId: string) {
  return request(`/api/rag/documents/ingestion-tasks/${encodeURIComponent(taskId)}`)
}
```

Add to `frontend/src/stores/knowledge.ts` state:

```ts
ingestionTask: null as null | Record<string, any>,
uploadError: '',
uploading: false,
```

Add action:

```ts
async uploadFile(payload: { title: string; knowledgeBase: string; visibility: string; metadata: string; file: File }) {
  this.uploading = true
  this.uploadError = ''
  try {
    const formData = new FormData()
    formData.append('title', payload.title)
    formData.append('knowledgeBase', payload.knowledgeBase)
    formData.append('visibility', payload.visibility)
    formData.append('metadata', payload.metadata || '{}')
    formData.append('file', payload.file)
    const result = await uploadKnowledgeFile(formData)
    this.ingestionTask = result
    if (result.document) {
      this.documents = [result.document, ...this.documents.filter((item) => item.id !== result.document.id)]
    }
    return result
  } catch (error: any) {
    this.uploadError = error?.message || '文件导入失败'
    throw error
  } finally {
    this.uploading = false
  }
}
```

- [ ] **Step 4: Run focused frontend tests**

Run:

```powershell
cd frontend
npm.cmd run test -- src/api/knowledge.test.ts src/stores/knowledge.test.ts
```

Expected:

```text
Focused knowledge API/store tests pass.
```

---

## Task 4: Vue3 Knowledge Upload Panel

**Files:**
- Modify: `frontend/src/pages/app/KnowledgePage.vue`
- Test: `frontend/src/pages/app/knowledge-page.test.ts`

- [ ] **Step 1: Write failing page test**

In `frontend/src/pages/app/knowledge-page.test.ts`, add a test that verifies:

```ts
expect(wrapper.text()).toContain('文件导入')
expect(wrapper.text()).toContain('支持 txt、md、pdf')
```

Add an interaction test if existing test setup supports file inputs:

```ts
const input = wrapper.find('input[type="file"]')
expect(input.exists()).toBe(true)
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/knowledge-page.test.ts
```

Expected:

```text
Text "文件导入" not found.
```

- [ ] **Step 3: Implement upload panel**

Modify `KnowledgePage.vue` to add a section near the create-document form:

```vue
<section class="knowledge-upload-panel">
  <div>
    <p class="section-kicker">文件导入</p>
    <h2>从本地文件生成知识库文档</h2>
    <p class="muted">支持 txt、md、pdf。导入后会解析文本、清洗内容、切分 chunk，并进入现有 RAG 检索链路。</p>
  </div>

  <form class="knowledge-upload-form" @submit.prevent="submitUpload">
    <input v-model="uploadForm.title" placeholder="文档标题" />
    <select v-model="uploadForm.knowledgeBase">
      <option value="role">岗位知识库</option>
      <option value="question">题库 RAG</option>
      <option value="candidate">候选人画像</option>
    </select>
    <select v-model="uploadForm.visibility">
      <option value="private">私有</option>
      <option value="public">公开</option>
    </select>
    <input type="file" accept=".txt,.md,.pdf" @change="onFileChange" />
    <button type="submit" :disabled="knowledgeStore.uploading">导入文件</button>
  </form>

  <div v-if="knowledgeStore.ingestionTask" class="ingestion-result">
    <strong>导入状态：{{ knowledgeStore.ingestionTask.status }}</strong>
    <span v-if="knowledgeStore.ingestionTask.preview">
      文本长度 {{ knowledgeStore.ingestionTask.preview.textLength }}，chunk 数 {{ knowledgeStore.ingestionTask.preview.chunkCount }}
    </span>
  </div>
  <p v-if="knowledgeStore.uploadError" class="error-text">{{ knowledgeStore.uploadError }}</p>
</section>
```

Add script state and handlers following the page’s current composition style.

- [ ] **Step 4: Run focused page test**

Run:

```powershell
cd frontend
npm.cmd run test -- src/pages/app/knowledge-page.test.ts
```

Expected:

```text
Knowledge page tests pass.
```

---

## Task 5: Learning Doc And Roadmap

**Files:**
- Create: `docs/learning/20-RAG文档摄取链路如何从文件到chunk.md`
- Modify: `docs/roadmap/current-state.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/plans/README.md`

- [ ] **Step 1: Write learning document**

Create `docs/learning/20-RAG文档摄取链路如何从文件到chunk.md` with these sections:

```markdown
# 20 RAG 文档摄取链路如何从文件到 chunk

## 1. 为什么 RAG 不只是检索

## 2. 文件上传后后端做了什么

## 3. 文本解析、清洗、chunk 切分分别解决什么问题

## 4. 为什么需要 ingestion task

## 5. 它和 Celery / Redis 的关系

## 6. 面试时怎么讲
```

- [ ] **Step 2: Update roadmap and README files**

Update:

```text
docs/roadmap/current-state.md
docs/specs/README.md
docs/plans/README.md
```

State that current active stage is:

```text
RAG Document Ingestion V2：补齐文件上传、解析、清洗、chunk 预览、入库任务状态和 Vue3 文件导入入口。
```

- [ ] **Step 3: Run documentation sanity check**

Run:

```powershell
Test-Path 'docs\learning\20-RAG文档摄取链路如何从文件到chunk.md'
Test-Path 'docs\specs\active\rag-document-ingestion-v2-design.md'
Test-Path 'docs\plans\active\rag-document-ingestion-v2.md'
```

Expected:

```text
True
True
True
```

---

## Task 6: Full Verification And Archive

**Files:**
- Move after implementation:
  - `docs/specs/active/rag-document-ingestion-v2-design.md`
  - `docs/plans/active/rag-document-ingestion-v2.md`
- To:
  - `docs/specs/completed/rag-document-ingestion-v2-design.md`
  - `docs/plans/completed/rag-document-ingestion-v2.md`

- [ ] **Step 1: Run backend focused tests**

```powershell
python -m pytest tests/test_rag_document_ingestion.py tests/test_rag_documents_upload_route.py -q
```

- [ ] **Step 2: Run full backend tests**

```powershell
python -m pytest -q
```

- [ ] **Step 3: Run frontend focused tests**

```powershell
cd frontend
npm.cmd run test -- src/api/knowledge.test.ts src/stores/knowledge.test.ts src/pages/app/knowledge-page.test.ts
```

- [ ] **Step 4: Run full frontend tests and build**

```powershell
cd frontend
npm.cmd run test
npm.cmd run build
```

- [ ] **Step 5: Browser verification**

Open:

```text
http://127.0.0.1:5173/vue/app/knowledge
```

Verify:

- File import panel is visible.
- txt / md / pdf support text is visible.
- Uploading a txt file creates a document.
- New document appears in the knowledge list.
- Document detail shows chunks.
- Unsupported file type shows readable error.
- Desktop has no horizontal overflow.
- Mobile 390px has no horizontal overflow.

- [ ] **Step 6: Archive completed docs**

After all tests and browser checks pass:

```powershell
Move-Item -LiteralPath 'docs\specs\active\rag-document-ingestion-v2-design.md' -Destination 'docs\specs\completed\rag-document-ingestion-v2-design.md'
Move-Item -LiteralPath 'docs\plans\active\rag-document-ingestion-v2.md' -Destination 'docs\plans\completed\rag-document-ingestion-v2.md'
```

Update README/current-state to say active stage is empty and RAG Document Ingestion V2 is completed.
