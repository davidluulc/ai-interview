import { apiRequest } from "./client";

export interface HistoryApplicationProfile {
  id: number;
  title: string;
  targetRole?: string;
  applicationType?: string;
  positionTag?: string;
}

export interface HistoryAnswer {
  question: string;
  answer: string;
}

export interface HistoryRecord {
  id: number;
  createdAt: string;
  applicationProfile?: HistoryApplicationProfile | null;
  profile: Record<string, unknown>;
  answers: HistoryAnswer[];
  report: Record<string, unknown>;
}

export interface CreateHistoryPayload {
  applicationProfileId?: number | null;
  profile: Record<string, unknown>;
  answers: HistoryAnswer[];
  report: Record<string, unknown>;
}

export async function listHistory(): Promise<HistoryRecord[]> {
  return apiRequest<HistoryRecord[]>("/api/history");
}

export async function createHistory(payload: CreateHistoryPayload): Promise<HistoryRecord> {
  return apiRequest<HistoryRecord>("/api/history", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
