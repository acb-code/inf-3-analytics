import type {
  RunListResponse,
  RunDetailResponse,
  EventsResponse,
  EventFramesManifest,
  FrameAnalyticsResponse,
  PipelineStatusResponse,
  UploadResponse,
  TriggerPipelineRequest,
  PipelineStep,
  DeleteRunResponse,
} from "@/types/api";

// Treat an explicitly-empty NEXT_PUBLIC_INF3_API_BASE as "same-origin" (root-relative paths).
const API_BASE = process.env.NEXT_PUBLIC_INF3_API_BASE ?? "http://localhost:8000";
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

  // Upload
  uploadVideo: async (
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<UploadResponse> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append("file", file);

      xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable && onProgress) {
          const percent = Math.round((e.loaded / e.total) * 100);
          onProgress(percent);
        }
      });

      xhr.addEventListener("load", () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch {
            reject(new Error("Invalid response"));
          }
        } else {
          try {
            const error = JSON.parse(xhr.responseText);
            reject(new Error(error.detail || `Upload failed: ${xhr.status}`));
          } catch {
            reject(new Error(`Upload failed: ${xhr.status}`));
          }
        }
      });

      xhr.addEventListener("error", () => reject(new Error("Upload failed")));
      xhr.addEventListener("abort", () => reject(new Error("Upload cancelled")));

      xhr.open("POST", `${API_BASE}/upload`);
      xhr.send(formData);
    });
  },

  // Pipeline
  getPipelineStatus: (runId: string, options?: FetchOptions) =>
    fetchJson<PipelineStatusResponse>(`/runs/${runId}/pipeline/status`, options),

  startPipeline: async (
    runId: string,
    request?: TriggerPipelineRequest
  ): Promise<{ message: string; run_id: string; status_url: string }> => {
    const res = await fetch(`${API_BASE}/runs/${runId}/pipeline/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request || {}),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to start pipeline: ${res.status}`);
    }
    return res.json();
  },

  runPipelineStep: async (
    runId: string,
    stepName: PipelineStep,
    request?: TriggerPipelineRequest
  ): Promise<{ message: string; run_id: string; step: string; status_url: string }> => {
    const res = await fetch(`${API_BASE}/runs/${runId}/pipeline/step/${stepName}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request || {}),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to run step: ${res.status}`);
    }
    return res.json();
  },

  cancelPipeline: async (runId: string): Promise<{ message: string; run_id: string }> => {
    const res = await fetch(`${API_BASE}/runs/${runId}/pipeline/cancel`, {
      method: "POST",
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to cancel pipeline: ${res.status}`);
    }
    return res.json();
  },

  cancelPipelineStep: async (
    runId: string,
    stepName: PipelineStep
  ): Promise<{ message: string; run_id: string; step: string }> => {
    const res = await fetch(`${API_BASE}/runs/${runId}/pipeline/step/${stepName}/cancel`, {
      method: "POST",
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to cancel step: ${res.status}`);
    }
    return res.json();
  },

  deleteRun: async (runId: string): Promise<DeleteRunResponse> => {
    const res = await fetch(`${API_BASE}/runs/${runId}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to delete run: ${res.status}`);
    }
    return res.json();
  },

  /**
   * Stream pipeline status updates via Server-Sent Events.
   * Returns a cleanup function to close the connection.
   */
  streamPipelineStatus: (
    runId: string,
    callbacks: {
      onStatus?: (status: PipelineStatusResponse) => void;
      onDone?: (data: { run_status: string }) => void;
      onError?: (error: Error) => void;
    }
  ): (() => void) => {
    const url = `${API_BASE}/runs/${runId}/pipeline/stream`;
    const eventSource = new EventSource(url);

    eventSource.addEventListener("status", (event) => {
      try {
        const data = JSON.parse(event.data) as PipelineStatusResponse;
        callbacks.onStatus?.(data);
      } catch (err) {
        callbacks.onError?.(new Error("Failed to parse status event"));
      }
    });

    eventSource.addEventListener("done", (event) => {
      try {
        const data = JSON.parse(event.data) as { run_status: string };
        callbacks.onDone?.(data);
      } catch (err) {
        callbacks.onError?.(new Error("Failed to parse done event"));
      }
      eventSource.close();
    });

    eventSource.addEventListener("error", (event) => {
      // Check if it's just the connection closing (expected after done)
      if (eventSource.readyState === EventSource.CLOSED) {
        return;
      }
      callbacks.onError?.(new Error("SSE connection error"));
      eventSource.close();
    });

    // Return cleanup function
    return () => {
      eventSource.close();
    };
  },
};
