import type {
  RunListResponse,
  RunDetailResponse,
  EventsResponse,
  EventFramesManifest,
  FrameAnalyticsResponse,
} from "@/types/api";

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

  // Event frames
  getEventFramesManifest: (runId: string) =>
    fetchJson<EventFramesManifest>(`/runs/${runId}/artifacts/event-frames/manifest`),
  getEventFrameUrl: (runId: string, eventDir: string, frameFilename: string) =>
    `${API_BASE}/runs/${runId}/artifacts/event-frames/${eventDir}/frames/${frameFilename}`,

  // Frame analytics
  getFrameAnalytics: (runId: string, eventId: string) =>
    fetchJson<FrameAnalyticsResponse>(`/runs/${runId}/artifacts/frame-analytics/by-event/${eventId}`),
};
