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

export interface RagIngestionPreview {
  title?: string;
  textLength: number;
  chunkCount: number;
  warnings: string[];
}

export interface RagIngestionTask {
  id?: number;
  taskId: string;
  taskType?: string;
  status: string;
  title?: string;
  originalFilename?: string;
  knowledgeBase?: KnowledgeBaseType | string;
  progress?: number;
  message?: string;
  retryCount?: number;
  maxRetries?: number;
  canRetry?: boolean;
  hasTextSnapshot?: boolean;
  createdAt?: string | null;
  updatedAt?: string | null;
  completedAt?: string | null;
  result?: {
    document?: RagDocument;
    preview?: RagIngestionPreview;
  };
  error?: string;
  document?: RagDocument;
  preview?: RagIngestionPreview;
}

export interface RagIngestionTaskListResponse {
  items: RagIngestionTask[];
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

export function uploadKnowledgeFile(formData: FormData): Promise<RagIngestionTask> {
  return apiRequest<RagIngestionTask>("/api/rag/documents/upload", {
    method: "POST",
    body: formData
  });
}

export function getIngestionTask(taskId: string): Promise<RagIngestionTask> {
  return apiRequest<RagIngestionTask>(`/api/rag/documents/ingestion-tasks/${encodeURIComponent(taskId)}`);
}

export function getIngestionTasks(): Promise<RagIngestionTaskListResponse> {
  return apiRequest<RagIngestionTaskListResponse>("/api/rag/documents/ingestion-tasks");
}

export function retryIngestionTask(taskId: string): Promise<RagIngestionTask> {
  return apiRequest<RagIngestionTask>(`/api/rag/documents/ingestion-tasks/${encodeURIComponent(taskId)}/retry`, {
    method: "POST"
  });
}
