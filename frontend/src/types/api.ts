// Run status
export type RunStatus = "created" | "running" | "completed" | "failed";

// Artifact types
export type ArtifactType =
  | "transcript"
  | "events"
  | "event_frames_manifest"
  | "frame_analytics_manifest";

// Event types matching backend
export type EventType =
  | "structural_anomaly"
  | "safety_risk"
  | "maintenance_note"
  | "measurement"
  | "location_reference"
  | "uncertainty"
  | "observation"
  | "other";

// Severity levels
export type Severity = "low" | "medium" | "high";

// Transcript reference within an event
export interface TranscriptRef {
  segment_ids: number[];
  excerpt: string;
  keywords: string[];
}

// Single event from the events JSON
export interface Event {
  event_id: string;
  event_type: EventType;
  severity: Severity | null;
  confidence: number;
  start_s: number;
  end_s: number;
  start_ts: string;
  end_ts: string;
  title: string;
  summary: string;
  transcript_ref: TranscriptRef;
  suggested_actions: string[];
  metadata: {
    extractor_engine: string;
    extractor_version: string;
    created_at: string;
    source_transcript_path: string;
  };
  related_rule_events: unknown | null;
}

// Response from GET /runs/{run_id}/artifacts/events
export interface EventsResponse {
  events: Event[];
}

// Artifact availability info
export interface ArtifactInfo {
  type: ArtifactType;
  available: boolean;
  url: string | null;
}

// Run metadata
export interface RunMetadata {
  run_id: string;
  video_path: string;
  run_root: string;
  video_basename: string;
  status: RunStatus;
  created_at: string;
}

// Response from GET /runs
export interface RunListResponse {
  runs: RunMetadata[];
}

// Response from GET /runs/{run_id}
export interface RunDetailResponse {
  run: RunMetadata;
  artifacts: ArtifactInfo[];
}
