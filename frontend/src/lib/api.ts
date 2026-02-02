import type { RunListResponse, RunDetailResponse, EventsResponse } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_INF3_API_BASE || "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  listRuns: () => fetchJson<RunListResponse>("/runs"),
  getRun: (runId: string) => fetchJson<RunDetailResponse>(`/runs/${runId}`),
  getEvents: (runId: string) => fetchJson<EventsResponse>(`/runs/${runId}/artifacts/events`),
  getVideoUrl: (runId: string) => `${API_BASE}/runs/${runId}/video`,
};
