import type {
  RunListResponse,
  RunDetailResponse,
  EventsResponse,
  EventFramesManifest,
  FrameAnalyticsResponse,
} from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_INF3_API_BASE || "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 10000;

export interface FetchOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}

async function fetchJson<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const onAbort = () => controller.abort();
  options.signal?.addEventListener("abort", onAbort);

  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const signal = controller.signal;

  const res = await fetch(`${API_BASE}${path}`, { signal });
  clearTimeout(timeout);
  options.signal?.removeEventListener("abort", onAbort);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  listRuns: (options?: FetchOptions) => fetchJson<RunListResponse>("/runs", options),
  getRun: (runId: string, options?: FetchOptions) =>
    fetchJson<RunDetailResponse>(`/runs/${runId}`, options),
  getEvents: (runId: string, options?: FetchOptions) =>
    fetchJson<EventsResponse>(`/runs/${runId}/artifacts/events`, options),
  getVideoUrl: (runId: string) => `${API_BASE}/runs/${runId}/video`,

  // Event frames
  getEventFramesManifest: (runId: string, options?: FetchOptions) =>
    fetchJson<EventFramesManifest>(`/runs/${runId}/artifacts/event-frames/manifest`, options),
  getEventFrameUrl: (runId: string, eventDir: string, frameFilename: string) =>
    `${API_BASE}/runs/${runId}/artifacts/event-frames/${eventDir}/frames/${frameFilename}`,

  // Frame analytics
  getFrameAnalytics: (runId: string, eventId: string, options?: FetchOptions) =>
    fetchJson<FrameAnalyticsResponse>(
      `/runs/${runId}/artifacts/frame-analytics/by-event/${eventId}`,
      options
    ),
};
