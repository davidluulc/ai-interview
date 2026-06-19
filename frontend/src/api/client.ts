export const ACCESS_TOKEN_KEY = "ai_interview_access_token";
export const REFRESH_TOKEN_KEY = "ai_interview_refresh_token";

export interface ApiTokens {
  accessToken: string;
  refreshToken?: string;
}

export function setApiTokens(tokens: ApiTokens): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
  if (tokens.refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
  }
}

export function clearApiTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function getAccessToken(): string {
  return localStorage.getItem(ACCESS_TOKEN_KEY) || "";
}

export function getRefreshToken(): string {
  return localStorage.getItem(REFRESH_TOKEN_KEY) || "";
}

function buildHeaders(initHeaders?: HeadersInit, body?: BodyInit | null): Record<string, string> {
  const sourceHeaders = new Headers(initHeaders);
  const headers: Record<string, string> = {};
  sourceHeaders.forEach((value, key) => {
    headers[key] = value;
  });

  if (!sourceHeaders.has("Content-Type") && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const token = getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return headers;
}

async function readResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

export function normalizeApiErrorMessage(message: string, status = 0): string {
  const text = String(message || "");
  if (status === 504 || /504|Gateway Time-out|Gateway Timeout|timed out/i.test(text)) {
    return "模型响应超时，请稍后重试。本轮回答已保留。";
  }
  if (status === 502 || /<html|<body|Bad Gateway|502/i.test(text)) {
    return "服务暂时不可用，请稍后重试。";
  }
  return text || "请求失败";
}

function getErrorMessage(body: unknown, status = 0): string {
  if (typeof body === "object" && body && "error" in body) {
    const error = (body as { error?: unknown }).error;
    if (typeof error === "object" && error && "message" in error) {
      const message = String((error as { message?: unknown }).message || "");
      if (message.trim()) return normalizeApiErrorMessage(message, status);
    }
  }
  if (typeof body === "object" && body && "detail" in body) {
    return normalizeApiErrorMessage(String(body.detail), status);
  }
  if (typeof body === "string" && body.trim()) {
    return normalizeApiErrorMessage(body, status);
  }
  return normalizeApiErrorMessage("", status);
}

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return false;
  }

  const response = await fetch("/api/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken })
  });

  if (!response.ok) {
    clearApiTokens();
    return false;
  }

  const body = (await readResponseBody(response)) as ApiTokens;
  if (!body.accessToken) {
    clearApiTokens();
    return false;
  }

  setApiTokens({ accessToken: body.accessToken, refreshToken });
  return true;
}

export async function apiRequest<T = unknown>(
  path: string,
  init: RequestInit = {},
  retryOnUnauthorized = true
): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: buildHeaders(init.headers, init.body)
  });
  const body = await readResponseBody(response);

  if (response.ok) {
    return body as T;
  }

  if (response.status === 401 && retryOnUnauthorized && path !== "/api/auth/refresh") {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiRequest<T>(path, init, false);
    }
  }

  throw new Error(getErrorMessage(body, response.status));
}
