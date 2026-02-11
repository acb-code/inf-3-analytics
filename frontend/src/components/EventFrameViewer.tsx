"use client";

import {
  useState,
  useEffect,
  useCallback,
  type SyntheticEvent,
  type WheelEvent,
} from "react";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/api";
import type {
  EventFrameSet,
  FrameAnalysis,
  EventSummary,
  Detection,
} from "@/types/api";
import { formatTime, getSeverityColor } from "@/lib/format";

const MIN_ZOOM = 1;
const MAX_ZOOM = 4;
const ZOOM_STEP = 0.25;

type ViewerMode = "fit" | "zoom";

interface EventFrameViewerProps {
  runId: string;
  eventFrameSet: EventFrameSet;
  onClose: () => void;
}

export function EventFrameViewer({
  runId,
  eventFrameSet,
  onClose,
}: EventFrameViewerProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [frameAnalyses, setFrameAnalyses] = useState<FrameAnalysis[]>([]);
  const [eventSummary, setEventSummary] = useState<EventSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewerMode, setViewerMode] = useState<ViewerMode>("fit");
  const [zoom, setZoom] = useState(1);
  const [naturalSize, setNaturalSize] = useState<{ width: number; height: number } | null>(
    null
  );

  // Use server-provided event directory when available
  const eventDir = eventFrameSet.event_dir || getEventDirName(eventFrameSet);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    api
      .getFrameAnalytics(runId, eventFrameSet.event_id, { signal: controller.signal })
      .then((data) => {
        setFrameAnalyses(data.frame_analyses);
        setEventSummary(data.event_summary);
      })
      .catch((err) => {
        if (err?.name === "AbortError") return;
        if (err instanceof ApiError && err.status === 404) {
          // Frame analytics are optional; treat as "not available" rather than an error.
          setFrameAnalyses([]);
          setEventSummary(null);
          setError(null);
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load frame analytics");
        console.error("Failed to load frame analytics:", err);
      })
      .finally(() => {
        setLoading(false);
      });
    return () => controller.abort();
  }, [runId, eventFrameSet.event_id]);

  const currentFrame = eventFrameSet.frames[currentIndex];
  const currentAnalysis = frameAnalyses.find(
    (a) => a.frame_idx === currentIndex
  );

  const goToPrev = useCallback(() => {
    setCurrentIndex((i) => (i > 0 ? i - 1 : i));
  }, []);

  const goToNext = useCallback(() => {
    setCurrentIndex((i) =>
      i < eventFrameSet.frames.length - 1 ? i + 1 : i
    );
  }, [eventFrameSet.frames.length]);

  const clampZoom = useCallback((value: number) => {
    return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Number(value.toFixed(2))));
  }, []);

  const setFitMode = useCallback(() => {
    setViewerMode("fit");
  }, []);

  const setActualSize = useCallback(() => {
    setViewerMode("zoom");
    setZoom(1);
  }, []);

  const zoomIn = useCallback(() => {
    setViewerMode("zoom");
    setZoom((current) =>
      clampZoom((viewerMode === "fit" ? 1 : current) + ZOOM_STEP)
    );
  }, [clampZoom, viewerMode]);

  const zoomOut = useCallback(() => {
    setViewerMode("zoom");
    setZoom((current) =>
      clampZoom((viewerMode === "fit" ? 1 : current) - ZOOM_STEP)
    );
  }, [clampZoom, viewerMode]);

  const handleImageLoad = useCallback((e: SyntheticEvent<HTMLImageElement>) => {
    setNaturalSize({
      width: e.currentTarget.naturalWidth,
      height: e.currentTarget.naturalHeight,
    });
  }, []);

  const handleImageWheel = useCallback(
    (e: WheelEvent<HTMLDivElement>) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      if (e.deltaY < 0) {
        zoomIn();
      } else {
        zoomOut();
      }
    },
    [zoomIn, zoomOut]
  );

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable)
      ) {
        return;
      }

      if (e.key === "ArrowLeft") {
        goToPrev();
      } else if (e.key === "ArrowRight") {
        goToNext();
      } else if (e.key === "Escape") {
        onClose();
      } else if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        zoomIn();
      } else if (e.key === "-" || e.key === "_") {
        e.preventDefault();
        zoomOut();
      } else if (e.key === "0") {
        e.preventDefault();
        setActualSize();
      } else if (e.key.toLowerCase() === "f") {
        e.preventDefault();
        setFitMode();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goToPrev, goToNext, onClose, setActualSize, setFitMode, zoomIn, zoomOut]);

  // Get the image URL for current frame
  const frameFilename = currentFrame.path.split("/").pop() || "";
  const imageUrl = api.getEventFrameUrl(runId, eventDir, frameFilename);

  const frameWidth = currentFrame.width || naturalSize?.width || 0;
  const frameHeight = currentFrame.height || naturalSize?.height || 0;
  const zoomedWidth = frameWidth > 0 ? Math.round(frameWidth * zoom) : undefined;
  const zoomedHeight = frameHeight > 0 ? Math.round(frameHeight * zoom) : undefined;
  const zoomLabel = viewerMode === "fit" ? "Fit" : `${Math.round(zoom * 100)}%`;

  return (
    <div className="flex h-full flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-700 px-4 py-2">
        <div>
          <h3 className="text-sm font-medium text-white">
            {eventFrameSet.event_title}
          </h3>
          <p className="text-xs text-gray-400">
            {formatTime(eventFrameSet.start_s)} - {formatTime(eventFrameSet.end_s)}
          </p>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-white"
          title="Close (Esc)"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Main content */}
      <div className="flex min-h-0 flex-1 flex-col xl:flex-row">
        {/* Image section */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          {/* Image */}
          <div className="relative flex-1 min-h-0 bg-black">
            <div
              onWheel={handleImageWheel}
              className={`h-full w-full ${
                viewerMode === "fit"
                  ? "flex items-center justify-center overflow-hidden p-2"
                  : "overflow-auto p-2"
              }`}
            >
              <div
                className={
                  viewerMode === "zoom"
                    ? "flex min-h-full min-w-full items-center justify-center"
                    : ""
                }
              >
                <img
                  src={imageUrl}
                  alt={`Frame ${currentIndex + 1}`}
                  onLoad={handleImageLoad}
                  className={
                    viewerMode === "fit"
                      ? "max-h-full max-w-full object-contain"
                      : "block max-w-none"
                  }
                  style={
                    viewerMode === "zoom" && zoomedWidth && zoomedHeight
                      ? {
                          width: `${zoomedWidth}px`,
                          height: `${zoomedHeight}px`,
                        }
                      : undefined
                  }
                />
              </div>
            </div>

            {/* Navigation arrows */}
            <button
              onClick={goToPrev}
              disabled={currentIndex === 0}
              className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white hover:bg-black/70 disabled:opacity-30"
              title="Previous (Left Arrow)"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
              onClick={goToNext}
              disabled={currentIndex === eventFrameSet.frames.length - 1}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white hover:bg-black/70 disabled:opacity-30"
              title="Next (Right Arrow)"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>

          {/* Thumbnail strip */}
          <div className="flex gap-1 overflow-x-auto border-t border-gray-700 bg-gray-800 p-2">
            {eventFrameSet.frames.map((frame, idx) => {
              const thumbFilename = frame.path.split("/").pop() || "";
              const thumbUrl = api.getEventFrameUrl(runId, eventDir, thumbFilename);
              return (
                <button
                  key={frame.frame_id}
                  onClick={() => setCurrentIndex(idx)}
                  className={`flex-shrink-0 rounded border-2 ${
                    idx === currentIndex
                      ? "border-blue-500"
                      : "border-transparent hover:border-gray-500"
                  }`}
                >
                  <img
                    src={thumbUrl}
                    alt={`Frame ${idx + 1}`}
                    className="h-10 w-10 object-cover sm:h-12 sm:w-12"
                  />
                </button>
              );
            })}
          </div>

          {/* Frame info bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-gray-700 bg-gray-800 px-4 py-2 text-sm text-gray-300">
            <div className="flex items-center gap-3">
              <span>
                Frame {currentIndex + 1} of {eventFrameSet.frames.length}
              </span>
              <span className="font-mono">{formatTime(currentFrame.timestamp_s)}</span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={setFitMode}
                className={`rounded px-2 py-1 text-xs font-medium ${
                  viewerMode === "fit"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-700 text-gray-200 hover:bg-gray-600"
                }`}
                title="Fit image to viewport (F)"
              >
                Fit
              </button>
              <button
                onClick={setActualSize}
                className={`rounded px-2 py-1 text-xs font-medium ${
                  viewerMode === "zoom" && zoom === 1
                    ? "bg-blue-600 text-white"
                    : "bg-gray-700 text-gray-200 hover:bg-gray-600"
                }`}
                title="Reset to 100% (0)"
              >
                100%
              </button>
              <button
                onClick={zoomOut}
                className="rounded bg-gray-700 px-2 py-1 text-xs font-medium text-gray-200 hover:bg-gray-600 disabled:opacity-40"
                title="Zoom out (-)"
                disabled={viewerMode === "zoom" && zoom <= MIN_ZOOM}
              >
                -
              </button>
              <span className="w-12 text-center text-xs tabular-nums text-gray-300">
                {zoomLabel}
              </span>
              <button
                onClick={zoomIn}
                className="rounded bg-gray-700 px-2 py-1 text-xs font-medium text-gray-200 hover:bg-gray-600 disabled:opacity-40"
                title="Zoom in (+)"
                disabled={viewerMode === "zoom" && zoom >= MAX_ZOOM}
              >
                +
              </button>
            </div>
          </div>
        </div>

        {/* Analysis panel */}
        <div className="h-56 w-full flex-shrink-0 overflow-y-auto border-t border-gray-700 bg-gray-800 sm:h-64 xl:h-auto xl:w-80 xl:border-l xl:border-t-0">
          <div className="p-4">
            <h4 className="mb-3 text-sm font-medium text-white">VLM Analysis</h4>

            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-600 border-t-blue-500"></div>
              </div>
            ) : error ? (
              <div className="rounded border border-red-700/40 bg-red-900/30 p-3 text-xs text-red-200">
                {error}
              </div>
            ) : currentAnalysis ? (
              <div className="space-y-4">
                {/* Scene summary */}
                {currentAnalysis.scene_summary && (
                  <div>
                    <h5 className="mb-1 text-xs font-medium uppercase text-gray-400">
                      Scene Summary
                    </h5>
                    <p className="text-sm text-gray-200">
                      {currentAnalysis.scene_summary}
                    </p>
                  </div>
                )}

                {/* Detections */}
                {currentAnalysis.detections.length > 0 && (
                  <div>
                    <h5 className="mb-2 text-xs font-medium uppercase text-gray-400">
                      Detections ({currentAnalysis.detections.length})
                    </h5>
                    <div className="space-y-2">
                      {currentAnalysis.detections.map((det, idx) => (
                        <DetectionCard key={idx} detection={det} />
                      ))}
                    </div>
                  </div>
                )}

                {/* QA pairs */}
                {currentAnalysis.qa && currentAnalysis.qa.length > 0 && (
                  <div>
                    <h5 className="mb-2 text-xs font-medium uppercase text-gray-400">
                      Q&A
                    </h5>
                    <div className="space-y-2">
                      {currentAnalysis.qa.map((qa, idx) => (
                        <div key={idx} className="rounded bg-gray-700 p-2 text-xs">
                          <p className="font-medium text-gray-300">{qa.q}</p>
                          <p className="mt-1 text-gray-400">{qa.a}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Model info */}
                <div className="border-t border-gray-700 pt-3 text-xs text-gray-500">
                  <p>Model: {currentAnalysis.engine.model}</p>
                  <p>Provider: {currentAnalysis.engine.provider}</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400">No analysis available for this frame</p>
            )}

            {/* Event summary */}
            {eventSummary && eventSummary.top_findings.length > 0 && (
              <div className="mt-6 border-t border-gray-700 pt-4">
                <h4 className="mb-3 text-sm font-medium text-white">
                  Event Summary
                </h4>
                <div className="space-y-2">
                  {eventSummary.top_findings.map((finding, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded bg-gray-700 px-2 py-1 text-xs"
                    >
                      <span className="text-gray-200">{finding.label}</span>
                      <div className="flex items-center gap-2">
                        {finding.severity && (
                          <span
                            className={`rounded px-1.5 py-0.5 text-xs capitalize ${getSeverityColor(finding.severity as "low" | "medium" | "high")}`}
                          >
                            {finding.severity}
                          </span>
                        )}
                        <span className="text-gray-400">
                          {Math.round(finding.max_confidence * 100)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function DetectionCard({ detection }: { detection: Detection }) {
  return (
    <div className="rounded bg-gray-700 p-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium capitalize text-gray-200">
          {detection.label}
        </span>
        <span className="text-xs text-gray-400">
          {Math.round(detection.confidence * 100)}%
        </span>
      </div>
      <div className="mt-1 flex flex-wrap gap-1">
        <span className="rounded bg-gray-600 px-1.5 py-0.5 text-xs text-gray-300">
          {detection.type}
        </span>
        {detection.attributes.severity && (
          <span
            className={`rounded px-1.5 py-0.5 text-xs capitalize ${getSeverityColor(detection.attributes.severity as "low" | "medium" | "high")}`}
          >
            {detection.attributes.severity}
          </span>
        )}
      </div>
      {detection.attributes.notes && (
        <p className="mt-1 text-xs text-gray-400">{detection.attributes.notes}</p>
      )}
    </div>
  );
}

// Helper function to derive event directory name from event frame set
// Must match backend logic in frame_extraction/extract.py
function getEventDirName(eventFrameSet: EventFrameSet): string {
  // Extract the first number from event_id (e.g., "llm_location_reference_0_e5e60bc9" -> "0")
  const match = eventFrameSet.event_id.match(/(\d+)/);
  const idx = match ? match[1] : "0";

  // Sanitize title: replace spaces with underscores, remove non-alphanumeric, lowercase, max 12 chars
  const titlePart = eventFrameSet.event_title
    .replace(/ /g, "_")
    .replace(/[^a-zA-Z0-9_-]/g, "")
    .toLowerCase()
    .substring(0, 12);

  return `evt_${idx}_${titlePart || "event"}`;
}
