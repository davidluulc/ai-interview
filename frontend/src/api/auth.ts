import { apiRequest, getRefreshToken } from "./client";

export interface CurrentUser {
  id: number;
  email: string;
  username: string;
  role?: string;
}

export interface AuthResponse {
  accessToken?: string;
  refreshToken?: string;
  access_token?: string;
  refresh_token?: string;
  tokenType?: string;
  user?: CurrentUser;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function register(email: string, username: string, password: string): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, username, password })
  });
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/api/auth/me");
}

export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return;
  }

  await apiRequest("/api/auth/logout", {
    method: "POST",
    body: JSON.stringify({ refreshToken })
  });
}
