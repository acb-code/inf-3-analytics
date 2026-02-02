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

// Event frame info
export interface EventFrame {
  frame_id: string;
  path: string;
  timestamp_s: number;
  timestamp_ts: string;
  width: number;
  height: number;
  file_size_bytes: number;
}

// Event frame set from manifest
export interface EventFrameSet {
  event_id: string;
  event_title: string;
  start_s: number;
  end_s: number;
  start_ts: string;
  end_ts: string;
  frames: EventFrame[];
  status: string;
  error_message: string | null;
}

// Event frames manifest
export interface EventFramesManifest {
  event_frame_sets: EventFrameSet[];
  metadata: {
    policy_name: string;
    policy_params: Record<string, unknown>;
    video_path: string;
    video_duration_s: number;
    video_fps: number;
    video_width: number;
    video_height: number;
    events_path: string;
    extraction_timestamp: string;
    jpeg_quality: number;
  };
  total_frames: number;
  total_events: number;
  successful_events: number;
  skipped_events: number;
  failed_events: number;
}

// Detection from VLM analysis
export interface Detection {
  type: string;
  label: string;
  confidence: number;
  bbox: {
    x: number;
    y: number;
    w: number;
    h: number;
  } | null;
  attributes: {
    severity: string | null;
    materials: string[] | null;
    location_hint: string | null;
    notes: string | null;
  };
}

// QA pair from VLM analysis
export interface QAPair {
  q: string;
  a: string;
}

// Single frame analysis from VLM
export interface FrameAnalysis {
  event_id: string;
  frame_idx: number;
  timestamp_s: number;
  timestamp_ts: string;
  image_path: string;
  engine: {
    name: string;
    provider: string;
    model: string;
    prompt_version: string;
    version: string;
    config: Record<string, unknown>;
  };
  detections: Detection[];
  scene_summary: string;
  qa: QAPair[] | null;
  error: string | null;
}

// Event summary from frame analytics
export interface EventSummary {
  event_id: string;
  frame_count: number;
  analyzed_count: number;
  failed_count: number;
  time_range: {
    start_s: number;
    end_s: number;
  };
  top_findings: {
    type: string;
    label: string;
    max_confidence: number;
    frame_count: number;
    severity: string | null;
  }[];
  representative_frame: {
    frame_idx: number;
    image_path: string;
    timestamp_s: number;
  };
}

// Response from GET /runs/{run_id}/artifacts/frame-analytics/by-event/{event_id}
export interface FrameAnalyticsResponse {
  event_id: string;
  frame_analyses: FrameAnalysis[];
  event_summary: EventSummary | null;
}
