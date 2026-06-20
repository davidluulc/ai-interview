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
  goodCount?: number;
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

export interface AdminRagQualityKnowledgeBaseSummary {
  knowledgeBase: string;
  label: string;
  totalCount: number;
  goodCount: number;
  weakCount: number;
  emptyCount: number;
  unusedInPromptCount: number;
  readyChunkCount?: number;
}

export interface AdminRagQualityDiagnosticSummary {
  type: string;
  knowledgeBase?: string;
  label?: string;
  title: string;
  message: string;
  count: number;
}

export interface AdminRagQuality {
  summary: AdminRagQualitySummary;
  items: AdminRagQualityItem[];
  knowledgeBaseSummary?: AdminRagQualityKnowledgeBaseSummary[];
  diagnosticSummary?: AdminRagQualityDiagnosticSummary[];
}

export interface AdminRagIngestionTaskSummary {
  totalCount: number;
  runningCount: number;
  succeededCount: number;
  failedCount: number;
  retryableCount: number;
  failureStages?: Record<string, number>;
  averageDurationMs?: number;
  maxDurationMs?: number;
  idempotencyHitCount?: number;
}

export interface AdminRagIngestionTask {
  taskId: string;
  userEmail?: string;
  title: string;
  originalFilename: string;
  knowledgeBase: string;
  status: string;
  error?: string;
  retryCount?: number;
  maxRetries?: number;
  canRetry?: boolean;
  durationMs?: number;
  failureStage?: string;
  idempotencyHit?: boolean;
  retryLockedAt?: string | null;
  updatedAt?: string | null;
}

export interface AdminRagIngestionTasks {
  summary: AdminRagIngestionTaskSummary;
  items: AdminRagIngestionTask[];
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

export interface AdminForceLogoutResponse {
  ok: boolean;
  revokedSessions: number;
  revokedRefreshTokens: number;
}

export interface AdminAiDebugDiagnosticSummary extends AdminAiDebugDiagnostic {
  count: number;
}

export interface AdminAiDebugRagSummary {
  knowledgeBase: string;
  label: string;
  hitCount: number;
  quality: string;
  qualityLabel: string;
  occurrenceCount: number;
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

export interface AdminRuntimeReplayStep {
  step: number;
  node: string;
  title: string;
  detail: string;
}

export interface AdminRuntimeReplaySummary {
  threadId?: string;
  exists?: boolean;
  status?: string;
  summary?: string;
  timeline?: AdminRuntimeReplayStep[];
  risks?: string[];
  nextActions?: string[];
}

export interface AdminRuntimeReportReason {
  reason: string;
  count: number;
}

export interface AdminRuntimeReport {
  threadId?: string;
  totalRuns?: number;
  statusCounts?: Record<string, number>;
  fallbackCount?: number;
  humanReviewCount?: number;
  topQualityGateReasons?: AdminRuntimeReportReason[];
  summary?: string;
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
  replaySummary?: AdminRuntimeReplaySummary;
  runtimeReport?: AdminRuntimeReport;
  explanation?: string;
}

export interface AdminWorkflowObservation {
  title: string;
  runtime: string;
  fallbackUsed: boolean;
  fallbackReason?: string;
  nodes: Array<{ nodeName?: string; node?: string; fallbackUsed?: boolean }>;
  ragSummary: Array<{ retrieverLabel: string; hitCount: number; qualityLevel: string }>;
  checkpoint: {
    exists: boolean;
    threadId?: string;
    currentNode?: string;
    roundCount?: number;
    lastAction?: string;
    requiresHumanReview?: boolean;
  };
  qualityGate?: { passed?: boolean; reasons?: string[] };
}

export interface AdminAiDebugDetail {
  summary: Record<string, unknown>;
  rag: Record<string, unknown> & { summary?: AdminAiDebugRagSummary[] };
  agent: Record<string, unknown>;
  langgraph: AdminAiDebugLangGraph;
  workflowObservation?: AdminWorkflowObservation;
  diagnostics: AdminAiDebugDiagnostic[];
  diagnosticSummary?: AdminAiDebugDiagnosticSummary[];
}

export interface AdminObservabilityRagSummary {
  totalCount: number;
  goodCount: number;
  weakCount: number;
  emptyCount: number;
}

export interface AdminObservabilityAgentSummary {
  totalCount: number;
  fallbackCount: number;
  lowerDifficultyCount: number;
  deepenCount: number;
  switchTopicCount: number;
}

export interface AdminObservabilityInterviewItem {
  recordId: number;
  userId?: number | null;
  userEmail: string;
  applicationProfileId?: number | null;
  profileTitle: string;
  targetRole?: string;
  createdAt: string | null;
  questionCount: number;
  reportStatus: string;
  ragSummary: AdminObservabilityRagSummary;
  agentSummary: AdminObservabilityAgentSummary;
  relation?: Record<string, string>;
}

export interface AdminObservabilityTurn {
  turnIndex: number;
  question: string;
  answer: string;
  ragSummary: Array<{
    knowledgeBase: string;
    label: string;
    hitCount: number;
    qualityLabel: string;
    queryText?: string;
  }>;
  agentDecision?: {
    actionLabel: string;
    reason: string;
    fallbackUsed: boolean;
    relation?: string;
  } | null;
  diagnostics: string[];
  traceIds: number[];
  traceLinks?: Array<{
    traceId: number;
    label: string;
    requestType: string;
    nextActionLabel: string;
    relation: string;
    debugPath: string;
    threadId: string;
  }>;
}

export interface AdminObservabilityInterviewDetail {
  recordId: number;
  hierarchy?: {
    user?: { id?: number | null; email?: string };
    applicationProfile?: { id?: number | null; title?: string; targetRole?: string };
    interviewRecord?: { id?: number | null; reportStatus?: string; questionCount?: number };
  };
  overview: Record<string, unknown>;
  summary: {
    questionCount: number;
    ragSummary: AdminObservabilityRagSummary;
    agentSummary: AdminObservabilityAgentSummary;
  };
  turns: AdminObservabilityTurn[];
  unlinkedLogs: { ragLogCount: number; agentLogCount: number };
  traceRelation?: Record<string, string>;
}

export interface AdminDatabaseInfrastructure {
  dialect?: string;
  isLocalSqlite?: boolean;
  usesExternalService?: boolean;
  autoInitEnabled?: boolean;
  migrationTool?: string;
  maskedUrl?: string;
}

export interface AdminRedisInfrastructure {
  enabled?: boolean;
  status?: "disabled" | "ok" | "error" | string;
  url?: string;
  error?: string;
}

export interface AdminCeleryInfrastructure {
  status?: "eager" | "configured" | string;
  mode?: string;
  taskAlwaysEager?: boolean;
  workerRequired?: boolean;
  workerCommand?: string;
  brokerConfigured?: boolean;
  resultBackendConfigured?: boolean;
  brokerUrl?: string;
  resultBackend?: string;
  healthTask?: string;
  registeredTaskModules?: string[];
  workerReadiness?: {
    mode: string;
    readyForWorker: boolean;
    requiresExternalWorker: boolean;
    missingRequirements: string[];
    message: string;
  };
}

export interface AdminInfrastructureStatus {
  database?: AdminDatabaseInfrastructure;
  redis?: AdminRedisInfrastructure;
  celery?: AdminCeleryInfrastructure;
}

export interface AdminSecurityFeature {
  enabled?: boolean;
  backend?: string;
}

export interface AdminSecurityStatus {
  tokenBlacklist?: AdminSecurityFeature;
  rateLimit?: AdminSecurityFeature;
  idempotency?: AdminSecurityFeature;
  errorRedaction?: AdminSecurityFeature;
}

export interface AdminConfig {
  modelName: string;
  embeddingModel: string;
  rerankModel: string;
  databaseUrl: string;
  infrastructure?: AdminInfrastructureStatus;
  security?: AdminSecurityStatus;
}

export function fetchAdminSummary(): Promise<AdminSummary> {
  return apiRequest<AdminSummary>("/api/admin/summary");
}

export function fetchAdminUsers(): Promise<AdminListResponse<AdminUser>> {
  return apiRequest<AdminListResponse<AdminUser>>("/api/admin/users");
}

export function forceLogoutUser(userId: number): Promise<AdminForceLogoutResponse> {
  return apiRequest<AdminForceLogoutResponse>(`/api/admin/users/${userId}/force-logout`, { method: "POST" });
}

export function fetchAdminRagDocuments(): Promise<AdminListResponse<AdminRagDocument>> {
  return apiRequest<AdminListResponse<AdminRagDocument>>("/api/admin/rag/documents");
}

export function fetchAdminRagQuality(): Promise<AdminRagQuality> {
  return apiRequest<AdminRagQuality>("/api/admin/rag/quality");
}

export function fetchAdminRagIngestionTasks(): Promise<AdminRagIngestionTasks> {
  return apiRequest<AdminRagIngestionTasks>("/api/admin/rag/ingestion-tasks");
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

export function fetchAdminObservabilityInterviews(): Promise<{
  items: AdminObservabilityInterviewItem[];
  total: number;
}> {
  return apiRequest("/api/admin/observability/interviews");
}

export function fetchAdminObservabilityInterviewDetail(recordId: number): Promise<AdminObservabilityInterviewDetail> {
  return apiRequest<AdminObservabilityInterviewDetail>(`/api/admin/observability/interviews/${recordId}`);
}

export function fetchAdminConfig(): Promise<AdminConfig> {
  return apiRequest<AdminConfig>("/api/admin/config");
}
