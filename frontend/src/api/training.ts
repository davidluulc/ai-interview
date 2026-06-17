import { apiRequest } from "./client";

export type TrainingTaskStatus = "todo" | "in_progress" | "done" | "archived";
export type TrainingTaskPriority = "low" | "medium" | "high";
export type TrainingAnswerStatus = "不会" | "模糊" | "完整";

export interface TrainingTask {
  id: number;
  applicationProfileId?: number | null;
  sourceInterviewRecordId?: number | null;
  weakTag: string;
  weakLabel?: string;
  title: string;
  description: string;
  status: TrainingTaskStatus;
  priority: TrainingTaskPriority;
  masteryScore: number;
  attemptCount?: number;
  lastPracticedAt?: string;
  nextReviewAt?: string;
  metadata?: Record<string, unknown>;
  createdAt?: string;
  updatedAt?: string;
}

export interface TrainingTaskListResponse {
  items: TrainingTask[];
}

export interface TrainingPractice {
  weakTag: string;
  weakLabel?: string;
  mode: "coach" | "interview";
  difficulty: "basic" | "medium" | "hard";
  question: string;
  answerKeyPoints: string[];
  commonMistakes: string[];
  oneMinuteTemplate?: string;
  relatedTags?: string[];
  rubric: string[];
  fallbackUsed?: boolean;
}

export interface TrainingPracticeResponse {
  task: TrainingTask;
  practice: TrainingPractice;
}

export interface GenerateTrainingTasksPayload {
  applicationProfileId?: number | null;
  sourceInterviewRecordId?: number | null;
  report: Record<string, unknown>;
}

export interface CompleteTrainingTaskPayload {
  answerStatus: TrainingAnswerStatus;
  answerText?: string;
  selfRating?: number | null;
}

export async function listTrainingTasks(status = ""): Promise<TrainingTaskListResponse> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<TrainingTaskListResponse>(`/api/training/tasks${query}`);
}

export async function generateTrainingTasksFromReport(
  payload: GenerateTrainingTasksPayload
): Promise<TrainingTaskListResponse> {
  return apiRequest<TrainingTaskListResponse>("/api/training/tasks/generate-from-report", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function startTrainingTask(taskId: number): Promise<TrainingTask> {
  return apiRequest<TrainingTask>(`/api/training/tasks/${taskId}/start`, { method: "POST" });
}

export async function getTrainingPractice(
  taskId: number,
  mode = "coach",
  difficulty = "basic"
): Promise<TrainingPracticeResponse> {
  return apiRequest<TrainingPracticeResponse>(
    `/api/training/tasks/${taskId}/practice?mode=${encodeURIComponent(mode)}&difficulty=${encodeURIComponent(
      difficulty
    )}`
  );
}

export async function completeTrainingTask(
  taskId: number,
  payload: TrainingAnswerStatus | CompleteTrainingTaskPayload = "完整"
): Promise<TrainingTask> {
  const body = typeof payload === "string" ? { answerStatus: payload } : payload;
  return apiRequest<TrainingTask>(`/api/training/tasks/${taskId}/complete`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function archiveTrainingTask(taskId: number): Promise<TrainingTask> {
  return apiRequest<TrainingTask>(`/api/training/tasks/${taskId}/archive`, { method: "POST" });
}
