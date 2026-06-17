import { apiRequest } from "./client";

export interface AdminSummary {
  userCount: number;
  interviewRecordCount: number;
  ragDocumentCount: number;
  ragRetrievalLogCount: number;
  agentDecisionLogCount: number;
}

export interface AdminUser {
  id: number;
  email: string;
  username: string;
  role: "admin" | "user" | string;
  createdAt: string | null;
}

export interface AdminListResponse<T> {
  items: T[];
}

export interface AdminRagDocument {
  id: number;
  title: string;
  knowledgeBase?: string;
  knowledge_base?: string;
  status?: string;
  visibility?: string;
  chunkCount?: number;
  chunk_count?: number;
  duplicateChunkCount?: number;
  duplicate_chunk_count?: number;
  userId?: number;
  userEmail?: string;
  updatedAt?: string | null;
  updated_at?: string | null;
}

export interface AdminRagQualitySummary {
  totalLogCount: number;
  lowQualityCount: number;
  emptyRecallCount: number;
  weakRecallCount: number;
  unusedInPromptCount: number;
}

export interface AdminRagQualityItem {
  id?: number;
  queryText?: string;
  query_text?: string;
  retrieverName?: string;
  retriever_name?: string;
  hitCount?: number;
  hit_count?: number;
  issueType?: string;
  recommendation?: string;
  createdAt?: string | null;
}

export interface AdminRagQuality {
  summary: AdminRagQualitySummary;
  items: AdminRagQualityItem[];
}

export interface AdminAgentLog {
  id?: number;
  nextAction?: string;
  next_action?: string;
  stage?: string;
  difficulty?: string;
  focus?: string;
  reason?: string;
  fallbackUsed?: boolean;
  fallback_used?: number | boolean;
  createdAt?: string | null;
}

export interface AdminAiDebugDiagnostic {
  type: string;
  level: "info" | "warning" | "error" | string;
  title: string;
  message: string;
}

export interface AdminAiDebugRecentItem {
  traceId: number;
  createdAt: string | null;
  userId: number;
  applicationProfileId: number | null;
  requestType: string;
  agentMode: string;
  nextAction: string;
  nextActionLabel: string;
  difficulty: string;
  fallbackUsed: boolean;
  totalRagHits: number;
  threadId: string;
  diagnostics: AdminAiDebugDiagnostic[];
}

export interface AdminRuntimeQualityGate {
  passed?: boolean;
  fallbackToClassic?: boolean;
  riskLevel?: string;
  reasons?: string[];
  checks?: Record<string, boolean>;
}

export interface AdminRuntimeComparisonSummary {
  visibleRuntime?: string;
  comparison?: {
    actionMatched?: boolean;
    difficultyMatched?: boolean;
    qualityGatePassed?: boolean;
    fallbackToClassic?: boolean;
    reasons?: string[];
  };
}

export interface AdminRuntimeAudit {
  requestedRuntime?: string;
  allowedRuntime?: string;
  visibleRuntime?: string;
  fallbackRuntime?: string;
  fallbackUsed?: boolean;
  qualityGatePassed?: boolean;
  qualityGateReasons?: string[];
  policyReasons?: string[];
  checkpointExists?: boolean;
  requiresHumanReview?: boolean;
}

export interface AdminAiDebugLangGraph {
  exists?: boolean;
  runtime?: string;
  visibleRuntime?: string;
  status?: string;
  currentNode?: string;
  threadId?: string;
  nodeTraceCount?: number;
  requiresHumanReview?: boolean;
  interrupt?: Record<string, unknown> | null;
  resumeDecision?: string;
  runtimeTrace?: Record<string, unknown>[];
  qualityGate?: AdminRuntimeQualityGate;
  comparisonSummary?: AdminRuntimeComparisonSummary;
  runtimeAudit?: AdminRuntimeAudit;
  explanation?: string;
}

export interface AdminAiDebugDetail {
  summary: Record<string, unknown>;
  rag: Record<string, unknown>;
  agent: Record<string, unknown>;
  langgraph: AdminAiDebugLangGraph;
  diagnostics: AdminAiDebugDiagnostic[];
}

export interface AdminConfig {
  modelName: string;
  embeddingModel: string;
  rerankModel: string;
  databaseUrl: string;
}

export function fetchAdminSummary(): Promise<AdminSummary> {
  return apiRequest<AdminSummary>("/api/admin/summary");
}

export function fetchAdminUsers(): Promise<AdminListResponse<AdminUser>> {
  return apiRequest<AdminListResponse<AdminUser>>("/api/admin/users");
}

export function fetchAdminRagDocuments(): Promise<AdminListResponse<AdminRagDocument>> {
  return apiRequest<AdminListResponse<AdminRagDocument>>("/api/admin/rag/documents");
}

export function fetchAdminRagQuality(): Promise<AdminRagQuality> {
  return apiRequest<AdminRagQuality>("/api/admin/rag/quality");
}

export function fetchAdminAgentLogs(): Promise<AdminListResponse<AdminAgentLog>> {
  return apiRequest<AdminListResponse<AdminAgentLog>>("/api/admin/agent/logs");
}

export function fetchAdminAiDebugRecent(): Promise<AdminListResponse<AdminAiDebugRecentItem>> {
  return apiRequest<AdminListResponse<AdminAiDebugRecentItem>>("/api/admin/ai-debug/recent");
}

export function fetchAdminAiDebugDetail(traceId: number): Promise<AdminAiDebugDetail> {
  return apiRequest<AdminAiDebugDetail>(`/api/admin/ai-debug/${traceId}`);
}

export function fetchAdminConfig(): Promise<AdminConfig> {
  return apiRequest<AdminConfig>("/api/admin/config");
}
