// Run status
export type RunStatus = "created" | "running" | "completed" | "failed";

// Pipeline step names
export type PipelineStep =
  | "transcribe"
  | "extract_events"
  | "extract_frames"
  | "frame_analytics";

// Pipeline step status
export type StepStatus = "pending" | "running" | "completed" | "failed" | "skipped";

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
    source?: "auto" | "manual";
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
  language?: string;
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
  event_dir?: string | null;
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

// Pipeline step info
export interface PipelineStepInfo {
  step: PipelineStep;
  status: StepStatus;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  output: string | null;
  progress_current: number | null;
  progress_total: number | null;
  progress_unit: string | null;
  progress_message: string | null;
  pid: number | null;
}

// Response from GET /runs/{run_id}/pipeline/status
export interface PipelineStatusResponse {
  run_id: string;
  run_status: RunStatus;
  steps: PipelineStepInfo[];
  progress_percent: number;
}

// Response from POST /upload
export interface UploadResponse {
  run_id: string;
  video_path: string;
  run_root: string;
  message: string;
  language?: string;
}

// Request for POST /runs/{run_id}/pipeline/start
export interface TriggerPipelineRequest {
  steps?: PipelineStep[];
  transcription_engine?: string;
  event_engine?: string;
  frame_analytics_engine?: string;
  language?: string;
}

export interface DeleteRunResponse {
  message: string;
  run_id: string;
}

// Decomposition types

export type DecompositionJobStatus =
  | "analyzing"
  | "splitting"
  | "creating_runs"
  | "completed"
  | "failed";

export interface SplitPoint {
  timestamp_s: number;
  timestamp_ts: string;
  type: "silence" | "scene" | "interval" | "user";
  keyframe_s: number;
  confidence: number;
}

export interface SegmentPreview {
  index: number;
  start_s: number;
  end_s: number;
  duration_s: number;
  start_ts: string;
  end_ts: string;
  estimated_size_mb: number;
}

export interface DecompositionPlanResponse {
  video_path: string;
  duration_s: number;
  duration_ts: string;
  file_size_mb: number;
  suggested_splits: SplitPoint[];
  estimated_segments: SegmentPreview[];
}

export interface AnalyzeDecompositionRequest {
  video_path: string;
  target_segment_duration_s?: number;
  silence_threshold_db?: number;
}

export interface ExecuteDecompositionRequest {
  video_path: string;
  split_timestamps: number[];
  create_child_runs?: boolean;
  parent_run_id?: string | null;
}

export interface SegmentResult {
  index: number;
  path: string;
  start_s: number;
  end_s: number;
  duration_s: number;
  file_size_mb: number;
  child_run_id: string | null;
}

export interface DecompositionStatusResponse {
  job_id: string;
  status: DecompositionJobStatus;
  progress_current: number;
  progress_total: number;
  progress_message: string | null;
  segments_created: SegmentResult[];
  child_run_ids: string[];
  error_message: string | null;
}

export interface DecompositionJobResponse {
  job_id: string;
  message: string;
  status_url: string;
}

// Event management types

export interface CreateEventRequest {
  start_s: number;
  end_s: number;
  event_type: EventType;
  severity?: Severity | null;
  title: string;
  summary: string;
}

export interface CreateCommentRequest {
  text: string;
}

export interface EventComment {
  comment_id: string;
  event_id: string;
  text: string;
  created_at: string;
}
