import type { CustomEmailInput, MockEmailSummary, StartRunResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function fetchMockEmails(): Promise<MockEmailSummary[]> {
  return request<MockEmailSummary[]>("/mock-emails");
}

export function startRunFromSample(emailId: string): Promise<StartRunResponse> {
  return request<StartRunResponse>("/runs", {
    method: "POST",
    body: JSON.stringify({ email_id: emailId }),
  });
}

export function startRunFromCustom(input: CustomEmailInput): Promise<StartRunResponse> {
  return request<StartRunResponse>("/runs/custom", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
