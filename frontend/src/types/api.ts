// Event types matching backend EventType enum
export type EventType =
  | "structural_anomaly"
  | "material_defect"
  | "safety_hazard"
  | "maintenance_issue"
  | "environmental"
  | "equipment"
  | "observation"
  | "location_marker"
  | "measurement"
  | "other";

// Severity levels
export type Severity = "low" | "medium" | "high";

// Run status
export type RunStatus = "pending" | "processing" | "completed" | "failed";

// Transcript reference for an event
export interface TranscriptReference {
  text: string;
  start_s: number;
  end_s: number;
}

// Single event from the event list
export interface Event {
  event_id: string;
  event_type: EventType;
  title: string;
  summary: string;
  severity: Severity;
  start_s: number;
  end_s: number;
  start_ts: string;
  end_ts: string;
  transcript_refs: TranscriptReference[];
  keywords: string[];
  confidence: number;
  engine: string;
}

// Event list response
export interface EventList {
  run_id: string;
  events: Event[];
  engine_info: {
    name: string;
    version: string;
  };
}

// Artifact availability info
export interface ArtifactInfo {
  available: boolean;
  path?: string;
  count?: number;
}

// Run metadata for list view
export interface RunMetadata {
  run_id: string;
  status: RunStatus;
  created_at: string;
  video_filename?: string;
  duration_s?: number;
}

// Response from GET /runs
export interface RunListResponse {
  runs: RunMetadata[];
  total: number;
}

// Response from GET /runs/{run_id}
export interface RunDetailResponse {
  run_id: string;
  status: RunStatus;
  created_at: string;
  video_filename?: string;
  duration_s?: number;
  artifacts: {
    transcript: ArtifactInfo;
    events: ArtifactInfo;
    frames: ArtifactInfo;
    frame_analytics: ArtifactInfo;
  };
}
