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
  AnalyzeDecompositionRequest,
  DecompositionPlanResponse,
  ExecuteDecompositionRequest,
  DecompositionJobResponse,
  DecompositionStatusResponse,
  CreateEventRequest,
  CreateCommentRequest,
  EventComment,
  Event,
  SiteCountsTimeSeries,
  SiteAnalyticsFramesResponse,
  UpdateEventRequest,
} from "@/types/api";

// Treat an explicitly-empty NEXT_PUBLIC_INF3_API_BASE as "same-origin" (root-relative paths).
const API_BASE = process.env.NEXT_PUBLIC_INF3_API_BASE ?? "http://localhost:8000";
const DEFAULT_TIMEOUT_MS = 10000;

export class ApiError extends Error {
  status: number;
  statusText: string;
  url: string;
  detail?: string;

  constructor(args: { status: number; statusText: string; url: string; detail?: string }) {
    const detailSuffix = args.detail ? ` - ${args.detail}` : "";
    super(`API error: ${args.status} ${args.statusText} (${args.url})${detailSuffix}`);
    this.name = "ApiError";
    this.status = args.status;
    this.statusText = args.statusText;
    this.url = args.url;
    this.detail = args.detail;
  }
}

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

  const url = `${API_BASE}${path}`;
  const res = await fetch(url, { signal });
  clearTimeout(timeout);
  options.signal?.removeEventListener("abort", onAbort);
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const contentType = res.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const body = (await res.json()) as unknown;
        if (body && typeof body === "object" && "detail" in body) {
          const raw = (body as { detail?: unknown }).detail;
          if (typeof raw === "string") detail = raw;
          else if (raw != null) detail = JSON.stringify(raw);
        }
      } else {
        const text = await res.text();
        if (text) detail = text.slice(0, 300);
      }
    } catch {
      // Ignore parse errors; fall back to status/statusText only.
    }
    throw new ApiError({ status: res.status, statusText: res.statusText, url, detail });
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
    onProgress?: (percent: number) => void,
    language?: string
  ): Promise<UploadResponse> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append("file", file);
      if (language) {
        formData.append("language", language);
      }

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

  deleteRun: async (runId: string, force = false): Promise<DeleteRunResponse> => {
    const url = force ? `${API_BASE}/runs/${runId}?force=true` : `${API_BASE}/runs/${runId}`;
    const res = await fetch(url, {
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
      onPing?: () => void;
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

    eventSource.addEventListener("ping", () => {
      callbacks.onPing?.();
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

  // Site analytics
  getSiteAnalyticsCounts: (runId: string, options?: FetchOptions) =>
    fetchJson<SiteCountsTimeSeries>(`/runs/${runId}/artifacts/site-analytics/counts`, options),

  getSiteAnalyticsFrames: (runId: string, offset = 0, limit = 50, options?: FetchOptions) =>
    fetchJson<SiteAnalyticsFramesResponse>(
      `/runs/${runId}/artifacts/site-analytics/frames?offset=${offset}&limit=${limit}`,
      options
    ),

  getSiteAnalyticsFrameUrl: (runId: string, frameFilename: string) =>
    `${API_BASE}/runs/${runId}/artifacts/site-analytics/frames/${frameFilename}`,

  // Decomposition
  analyzeForDecomposition: async (
    request: AnalyzeDecompositionRequest
  ): Promise<DecompositionPlanResponse> => {
    const res = await fetch(`${API_BASE}/decompose/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to analyze video: ${res.status}`);
    }
    return res.json();
  },

  executeDecomposition: async (
    request: ExecuteDecompositionRequest
  ): Promise<DecompositionJobResponse> => {
    const res = await fetch(`${API_BASE}/decompose/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to start decomposition: ${res.status}`);
    }
    return res.json();
  },

  getDecompositionStatus: (jobId: string, options?: FetchOptions) =>
    fetchJson<DecompositionStatusResponse>(`/decompose/${jobId}/status`, options),

  streamDecompositionStatus: (
    jobId: string,
    callbacks: {
      onStatus?: (status: DecompositionStatusResponse) => void;
      onDone?: (data: { status: string }) => void;
      onError?: (error: Error) => void;
    }
  ): (() => void) => {
    const url = `${API_BASE}/decompose/${jobId}/stream`;
    const eventSource = new EventSource(url);

    eventSource.addEventListener("status", (event) => {
      try {
        const data = JSON.parse(event.data) as DecompositionStatusResponse;
        callbacks.onStatus?.(data);
      } catch {
        callbacks.onError?.(new Error("Failed to parse status event"));
      }
    });

    eventSource.addEventListener("done", (event) => {
      try {
        const data = JSON.parse(event.data) as { status: string };
        callbacks.onDone?.(data);
      } catch {
        callbacks.onError?.(new Error("Failed to parse done event"));
      }
      eventSource.close();
    });

    eventSource.addEventListener("error", () => {
      if (eventSource.readyState === EventSource.CLOSED) {
        return;
      }
      callbacks.onError?.(new Error("SSE connection error"));
      eventSource.close();
    });

    return () => {
      eventSource.close();
    };
  },

  // Event management
  createEvent: async (runId: string, request: CreateEventRequest): Promise<Event> => {
    const res = await fetch(`${API_BASE}/runs/${runId}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to create event: ${res.status}`);
    }
    return res.json();
  },

  updateEvent: async (runId: string, eventId: string, request: UpdateEventRequest): Promise<Event> => {
    const res = await fetch(`${API_BASE}/runs/${runId}/events/${eventId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to update event: ${res.status}`);
    }
    return res.json();
  },

  deleteEvent: async (runId: string, eventId: string): Promise<{ message: string; event_id: string }> => {
    const res = await fetch(`${API_BASE}/runs/${runId}/events/${eventId}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to delete event: ${res.status}`);
    }
    return res.json();
  },

  getComments: async (runId: string, eventId: string, options?: FetchOptions): Promise<EventComment[]> => {
    return fetchJson<EventComment[]>(`/runs/${runId}/events/${eventId}/comments`, options);
  },

  createComment: async (
    runId: string,
    eventId: string,
    request: CreateCommentRequest
  ): Promise<EventComment> => {
    const res = await fetch(`${API_BASE}/runs/${runId}/events/${eventId}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to create comment: ${res.status}`);
    }
    return res.json();
  },

  deleteComment: async (
    runId: string,
    eventId: string,
    commentId: string
  ): Promise<{ message: string; comment_id: string }> => {
    const res = await fetch(`${API_BASE}/runs/${runId}/events/${eventId}/comments/${commentId}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || `Failed to delete comment: ${res.status}`);
    }
    return res.json();
  },
};
