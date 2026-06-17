export type TrainingTaskStatus = "todo" | "in_progress" | "done" | "archived";

export interface TrainingTaskView {
  id: number;
  weakTag: string;
  weakLabel?: string;
  title: string;
  description?: string;
  status: TrainingTaskStatus;
  priority?: "low" | "medium" | "high";
  masteryScore?: number;
  attemptCount?: number;
  nextReviewAt?: string;
  sourceInterviewRecordId?: number | null;
}
