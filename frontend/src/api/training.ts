import { apiRequest } from "./client";

export type TrainingTaskStatus = "todo" | "in_progress" | "done" | "archived";
export type TrainingTaskPriority = "low" | "medium" | "high";

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

export interface GenerateTrainingTasksPayload {
  applicationProfileId?: number | null;
  sourceInterviewRecordId?: number | null;
  report: Record<string, unknown>;
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

export async function completeTrainingTask(taskId: number, answerStatus = "完整"): Promise<TrainingTask> {
  return apiRequest<TrainingTask>(`/api/training/tasks/${taskId}/complete`, {
    method: "POST",
    body: JSON.stringify({ answerStatus })
  });
}

export async function archiveTrainingTask(taskId: number): Promise<TrainingTask> {
  return apiRequest<TrainingTask>(`/api/training/tasks/${taskId}/archive`, { method: "POST" });
}
