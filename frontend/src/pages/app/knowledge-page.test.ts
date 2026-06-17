import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import KnowledgePage from "./KnowledgePage.vue";

const knowledgeStore = {
  documents: [
    {
      id: 1,
      title: "FastAPI Depends",
      knowledgeBase: "role_knowledge",
      sourceType: "manual",
      status: "enabled",
      visibility: "private",
      chunkCount: 2,
      duplicateChunkCount: 0,
      updatedAt: "2026-06-13T10:00:00"
    }
  ],
  filteredDocuments: [
    {
      id: 1,
      title: "FastAPI Depends",
      knowledgeBase: "role_knowledge",
      sourceType: "manual",
      status: "enabled",
      visibility: "private",
      chunkCount: 2,
      duplicateChunkCount: 0,
      updatedAt: "2026-06-13T10:00:00"
    }
  ],
  selectedDetail: {
    document: {
      id: 1,
      title: "FastAPI Depends",
      knowledgeBase: "role_knowledge",
      status: "enabled",
      visibility: "private"
    },
    chunks: [
      {
        id: 11,
        documentId: 1,
        chunkIndex: 0,
        content: "Depends 会把依赖函数的返回值注入接口。",
        chunkHash: "hash-1",
        metadata: { role: "Python 后端" }
      }
    ]
  },
  debugResult: {
    roleKnowledge: [{ title: "岗位知识命中", content: "FastAPI Depends" }],
    questionBank: [{ title: "题库命中", content: "请解释 Depends" }],
    candidateMemory: [{ title: "候选人画像命中", content: "做过 FastAPI 项目" }],
    quality: { roleKnowledge: { level: "good", hitCount: 1 } },
    explanations: { roleKnowledge: { summary: "命中岗位知识库" } }
  },
  loading: false,
  saving: false,
  debugLoading: false,
  uploading: false,
  error: "",
  uploadError: "",
  metadataError: "metadata 必须是合法 JSON 对象，例如 {\"role\":\"Python 后端\",\"level\":\"实习\"}。",
  ingestionTask: {
    status: "success",
    preview: { textLength: 128, chunkCount: 2, warnings: [] },
    document: { id: 2, title: "文件导入资料" }
  },
  knowledgeBaseFilter: "all",
  statusFilter: "all",
  visibilityFilter: "all",
  searchKeyword: "",
  enabledCount: 1,
  archivedCount: 0,
  loadDocuments: vi.fn(),
  createDocumentFromForm: vi.fn(),
  uploadFile: vi.fn(),
  loadDocumentDetail: vi.fn(),
  updateStatus: vi.fn(),
  removeDocument: vi.fn(),
  runDebug: vi.fn(),
  setFilters: vi.fn()
};

vi.mock("@/stores/knowledge", () => ({
  useKnowledgeStore: () => knowledgeStore
}));

describe("knowledge page", () => {
  beforeEach(() => {
    knowledgeStore.loadDocuments.mockReset();
    knowledgeStore.createDocumentFromForm.mockReset();
    knowledgeStore.uploadFile.mockReset();
    knowledgeStore.loadDocumentDetail.mockReset();
    knowledgeStore.updateStatus.mockReset();
    knowledgeStore.removeDocument.mockReset();
    knowledgeStore.runDebug.mockReset();
    knowledgeStore.setFilters.mockReset();
    knowledgeStore.createDocumentFromForm.mockResolvedValue(false);
    knowledgeStore.uploadFile.mockResolvedValue(false);
  });

  it("renders knowledge documents and readable rag labels", () => {
    const wrapper = mountPage();

    expect(knowledgeStore.loadDocuments).toHaveBeenCalled();
    expect(wrapper.text()).toContain("知识库");
    expect(wrapper.text()).toContain("FastAPI Depends");
    expect(wrapper.text()).toContain("岗位知识库");
    expect(wrapper.text()).toContain("启用中");
    expect(wrapper.text()).toContain("仅自己可用");
    expect(wrapper.text()).toContain("chunk 2");
  });

  it("updates filters from controls", async () => {
    const wrapper = mountPage();

    await wrapper.get('[data-testid="knowledge-base-filter"]').setValue("role_knowledge");
    expect(knowledgeStore.setFilters).toHaveBeenLastCalledWith({
      knowledgeBase: "role_knowledge",
      status: "all",
      visibility: "all",
      searchKeyword: ""
    });

    await wrapper.get('[data-testid="knowledge-search"]').setValue("Depends");
    expect(knowledgeStore.setFilters).toHaveBeenLastCalledWith({
      knowledgeBase: "all",
      status: "all",
      visibility: "all",
      searchKeyword: "Depends"
    });
  });

  it("submits create form and shows metadata errors", async () => {
    const wrapper = mountPage();

    await wrapper.get('[data-testid="toggle-create-document"]').trigger("click");
    await wrapper.get('[data-testid="document-title"]').setValue("RAG 日志");
    await wrapper.get('[data-testid="document-content"]').setValue("RAG 日志用于观察召回质量。");
    await wrapper.get('[data-testid="document-metadata"]').setValue("{bad json");
    await wrapper.get('[data-testid="submit-document"]').trigger("submit");

    expect(knowledgeStore.createDocumentFromForm).toHaveBeenCalledWith({
      title: "RAG 日志",
      knowledgeBase: "role_knowledge",
      sourceType: "manual",
      content: "RAG 日志用于观察召回质量。",
      visibility: "private",
      metadataJson: "{bad json"
    });
    expect(wrapper.text()).toContain("metadata 必须是合法 JSON 对象");
  });

  it("renders file upload panel and submits selected files", async () => {
    knowledgeStore.uploadFile.mockResolvedValue(true);
    const wrapper = mountPage();
    const file = new File(["FastAPI Depends"], "depends.txt", { type: "text/plain" });

    expect(wrapper.text()).toContain("文件导入");
    expect(wrapper.text()).toContain("支持 txt、md、pdf");
    expect(wrapper.find('[data-testid="knowledge-upload-file"]').exists()).toBe(true);

    await wrapper.get('[data-testid="knowledge-upload-title"]').setValue("FastAPI 文件导入");
    await wrapper.get('[data-testid="knowledge-upload-metadata"]').setValue('{"positionTag":"python_backend"}');
    const fileInput = wrapper.get<HTMLInputElement>('[data-testid="knowledge-upload-file"]');
    Object.defineProperty(fileInput.element, "files", {
      configurable: true,
      value: [file]
    });
    await fileInput.trigger("change");
    await wrapper.get('[data-testid="knowledge-upload-form"]').trigger("submit");

    expect(knowledgeStore.uploadFile).toHaveBeenCalledWith({
      title: "FastAPI 文件导入",
      knowledgeBase: "role_knowledge",
      visibility: "private",
      metadataJson: '{"positionTag":"python_backend"}',
      file
    });
    expect(wrapper.text()).toContain("导入状态：success");
    expect(wrapper.text()).toContain("文本长度 128");
  });

  it("opens detail, updates status and deletes with confirmation", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const wrapper = mountPage();

    await wrapper.get('[data-testid="open-document-1"]').trigger("click");
    expect(knowledgeStore.loadDocumentDetail).toHaveBeenCalledWith(1);
    expect(wrapper.text()).toContain("Depends 会把依赖函数的返回值注入接口。");

    await wrapper.get('[data-testid="disable-document-1"]').trigger("click");
    expect(knowledgeStore.updateStatus).toHaveBeenCalledWith(1, "disabled");

    await wrapper.get('[data-testid="delete-document-1"]').trigger("click");
    expect(knowledgeStore.removeDocument).toHaveBeenCalledWith(1);
  });

  it("runs rag debug and renders three retrieval groups", async () => {
    const wrapper = mountPage();

    await wrapper.get('[data-testid="debug-role"]').setValue("Python 后端");
    await wrapper.get('[data-testid="debug-stage"]').setValue("技术基础");
    await wrapper.get('[data-testid="run-rag-debug"]').trigger("submit");

    expect(knowledgeStore.runDebug).toHaveBeenCalledWith({
      candidateName: "",
      role: "Python 后端",
      positionTag: "",
      resume: "",
      jd: "",
      stage: "技术基础"
    });
    expect(wrapper.text()).toContain("岗位知识命中");
    expect(wrapper.text()).toContain("题库命中");
    expect(wrapper.text()).toContain("候选人画像命中");
    expect(wrapper.text()).toContain("命中岗位知识库");
  });
});

function mountPage() {
  return mount(KnowledgePage, {
    global: {
      stubs: {
        AppLayout: { template: "<main><slot /></main>" }
      }
    }
  });
}
