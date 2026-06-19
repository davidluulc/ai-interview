import { apiRequest } from "./client";

export interface ApplicationProfile {
  id: number;
  title: string;
  targetRole?: string;
  target_role?: string;
  applicationType?: string;
  application_type?: string;
  company?: string;
  jd?: string;
  resume?: string;
  positionTag?: string;
  position_tag?: string;
  status?: "active" | "archived" | string;
  createdAt?: string;
  created_at?: string;
  updatedAt?: string;
  updated_at?: string;
}

export interface CreateApplicationProfilePayload {
  title: string;
  targetRole: string;
  company: string;
  jd: string;
  resume: string;
  applicationType?: string;
  positionTag?: string;
}

export async function listProfiles(status = "active"): Promise<ApplicationProfile[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest<ApplicationProfile[]>(`/api/application-profiles${query}`);
}

export async function createProfile(payload: CreateApplicationProfilePayload): Promise<ApplicationProfile> {
  return apiRequest<ApplicationProfile>("/api/application-profiles", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function archiveProfile(profileId: number): Promise<ApplicationProfile> {
  return apiRequest<ApplicationProfile>(`/api/application-profiles/${profileId}`, { method: "DELETE" });
}

export async function restoreProfile(profileId: number): Promise<ApplicationProfile> {
  return apiRequest<ApplicationProfile>(`/api/application-profiles/${profileId}/restore`, { method: "POST" });
}
