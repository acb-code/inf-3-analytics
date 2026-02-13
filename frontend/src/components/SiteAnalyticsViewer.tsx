"use client";

import {
  useState,
  useEffect,
  useCallback,
  type SyntheticEvent,
  type WheelEvent,
} from "react";
import { api } from "@/lib/api";
import type {
  SiteFrameDetection,
  SiteCountsTimeSeries,
} from "@/types/api";
import { formatTime } from "@/lib/format";
import { BoundingBoxOverlay } from "./BoundingBoxOverlay";
import { DetectionToggleList } from "./DetectionToggleList";

const MIN_ZOOM = 1;
const MAX_ZOOM = 4;
const ZOOM_STEP = 0.25;

type ViewerMode = "fit" | "zoom";

interface SiteAnalyticsViewerProps {
  runId: string;
  language?: string;
  onClose: () => void;
}

export function SiteAnalyticsViewer({
  runId,
  language,
  onClose,
}: SiteAnalyticsViewerProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [frames, setFrames] = useState<SiteFrameDetection[]>([]);
  const [counts, setCounts] = useState<SiteCountsTimeSeries | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewerMode, setViewerMode] = useState<ViewerMode>("fit");
  const [zoom, setZoom] = useState(1);
  const [naturalSize, setNaturalSize] = useState<{ width: number; height: number } | null>(null);
  const [visibleDetections, setVisibleDetections] = useState<Set<number>>(new Set());

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    Promise.all([
      api.getSiteAnalyticsFrames(runId, 0, 9999, { signal: controller.signal }),
      api.getSiteAnalyticsCounts(runId, { signal: controller.signal }),
    ])
      .then(([framesData, countsData]) => {
        setFrames(framesData.frames);
        setCounts(countsData);
      })
      .catch((err) => {
        if (err?.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Failed to load site analytics");
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [runId]);

  // Update visible detections when frame changes
  const currentFrame = frames[currentIndex] as SiteFrameDetection | undefined;
  useEffect(() => {
    if (currentFrame) {
      setVisibleDetections(new Set(currentFrame.detections.map((_, i) => i)));
    }
  }, [currentIndex, currentFrame?.frame_idx]);

  const goToPrev = useCallback(() => {
    setCurrentIndex((i) => (i > 0 ? i - 1 : i));
  }, []);

  const goToNext = useCallback(() => {
    setCurrentIndex((i) => (i < frames.length - 1 ? i + 1 : i));
  }, [frames.length]);

  const clampZoom = useCallback((value: number) => {
    return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Number(value.toFixed(2))));
  }, []);

  const setFitMode = useCallback(() => setViewerMode("fit"), []);

  const setActualSize = useCallback(() => {
    setViewerMode("zoom");
    setZoom(1);
  }, []);

  const zoomIn = useCallback(() => {
    setViewerMode("zoom");
    setZoom((current) => clampZoom((viewerMode === "fit" ? 1 : current) + ZOOM_STEP));
  }, [clampZoom, viewerMode]);

  const zoomOut = useCallback(() => {
    setViewerMode("zoom");
    setZoom((current) => clampZoom((viewerMode === "fit" ? 1 : current) - ZOOM_STEP));
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
      if (e.deltaY < 0) zoomIn();
      else zoomOut();
    },
    [zoomIn, zoomOut]
  );

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) return;

      if (e.key === "ArrowLeft") goToPrev();
      else if (e.key === "ArrowRight") goToNext();
      else if (e.key === "Escape") onClose();
      else if (e.key === "+" || e.key === "=") { e.preventDefault(); zoomIn(); }
      else if (e.key === "-" || e.key === "_") { e.preventDefault(); zoomOut(); }
      else if (e.key === "0") { e.preventDefault(); setActualSize(); }
      else if (e.key.toLowerCase() === "f") { e.preventDefault(); setFitMode(); }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [goToPrev, goToNext, onClose, setActualSize, setFitMode, zoomIn, zoomOut]);

  const handleToggleDetection = useCallback((index: number) => {
    setVisibleDetections((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }, []);

  const handleShowAll = useCallback(() => {
    if (currentFrame) {
      setVisibleDetections(new Set(currentFrame.detections.map((_, i) => i)));
    }
  }, [currentFrame]);

  const handleHideAll = useCallback(() => setVisibleDetections(new Set()), []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-gray-900">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-600 border-t-blue-500"></div>
      </div>
    );
  }

  if (error || frames.length === 0) {
    return (
      <div className="flex h-full flex-col bg-gray-900">
        <div className="flex items-center justify-between border-b border-gray-700 px-4 py-2">
          <h3 className="text-sm font-medium text-white">Site Analytics</h3>
          <button onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-white" title="Close (Esc)">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <div className="flex flex-1 items-center justify-center p-8">
          <p className="text-sm text-gray-400">{error || "No frames available"}</p>
        </div>
      </div>
    );
  }

  const frameFilename = currentFrame!.image_path.split("/").pop() || "";
  const imageUrl = api.getSiteAnalyticsFrameUrl(runId, frameFilename);
  const frameWidth = naturalSize?.width || 0;
  const frameHeight = naturalSize?.height || 0;
  const zoomedWidth = frameWidth > 0 ? Math.round(frameWidth * zoom) : undefined;
  const zoomedHeight = frameHeight > 0 ? Math.round(frameHeight * zoom) : undefined;
  const zoomLabel = viewerMode === "fit" ? "Fit" : `${Math.round(zoom * 100)}%`;

  return (
    <div className="flex h-full flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-700 px-4 py-2">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-medium text-white">Site Analytics</h3>
          {language && (
            <span className="rounded bg-gray-700 px-1.5 py-0.5 text-[10px] font-medium uppercase text-gray-300">
              {language}
            </span>
          )}
          {currentFrame!.engine && (
            <span className="text-xs text-gray-500">
              {currentFrame!.engine.provider}/{currentFrame!.engine.model}
            </span>
          )}
        </div>
        <button onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-white" title="Close (Esc)">
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>

      {/* Main content */}
      <div className="flex min-h-0 flex-1 flex-col xl:flex-row">
        {/* Image section */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
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
                    : "flex h-full w-full items-center justify-center"
                }
              >
                <div
                  className="relative"
                  style={
                    viewerMode === "fit"
                      ? {
                          maxWidth: "100%",
                          maxHeight: "100%",
                          aspectRatio: naturalSize ? `${naturalSize.width} / ${naturalSize.height}` : undefined,
                        }
                      : zoomedWidth && zoomedHeight
                        ? { width: `${zoomedWidth}px`, height: `${zoomedHeight}px` }
                        : undefined
                  }
                >
                  <img
                    src={imageUrl}
                    alt={`Frame ${currentIndex + 1}`}
                    onLoad={handleImageLoad}
                    className={
                      viewerMode === "fit"
                        ? "block h-full w-full"
                        : "block h-full w-full"
                    }
                  />
                  <BoundingBoxOverlay
                    detections={currentFrame!.detections}
                    visibleIndices={visibleDetections}
                  />
                </div>
              </div>
            </div>

            {/* Navigation arrows */}
            <button
              onClick={goToPrev}
              disabled={currentIndex === 0}
              className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white hover:bg-black/70 disabled:opacity-30"
              title="Previous (Left Arrow)"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
            </button>
            <button
              onClick={goToNext}
              disabled={currentIndex === frames.length - 1}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white hover:bg-black/70 disabled:opacity-30"
              title="Next (Right Arrow)"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
            </button>
          </div>

          {/* Thumbnail strip */}
          <div className="flex gap-1 overflow-x-auto border-t border-gray-700 bg-gray-800 p-2">
            {frames.map((frame, idx) => {
              const thumbFilename = frame.image_path.split("/").pop() || "";
              const thumbUrl = api.getSiteAnalyticsFrameUrl(runId, thumbFilename);
              return (
                <button
                  key={frame.frame_idx}
                  onClick={() => setCurrentIndex(idx)}
                  className={`flex-shrink-0 rounded border-2 ${
                    idx === currentIndex ? "border-blue-500" : "border-transparent hover:border-gray-500"
                  }`}
                >
                  <img src={thumbUrl} alt={`Frame ${idx + 1}`} className="h-10 w-10 object-cover sm:h-12 sm:w-12" />
                </button>
              );
            })}
          </div>

          {/* Frame info bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-gray-700 bg-gray-800 px-4 py-2 text-sm text-gray-300">
            <div className="flex items-center gap-3">
              <span>Frame {currentIndex + 1} of {frames.length}</span>
              <span className="font-mono">{formatTime(currentFrame!.timestamp_s)}</span>
            </div>
            <div className="flex items-center gap-1">
              <button onClick={setFitMode} className={`rounded px-2 py-1 text-xs font-medium ${viewerMode === "fit" ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-200 hover:bg-gray-600"}`} title="Fit (F)">Fit</button>
              <button onClick={setActualSize} className={`rounded px-2 py-1 text-xs font-medium ${viewerMode === "zoom" && zoom === 1 ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-200 hover:bg-gray-600"}`} title="100% (0)">100%</button>
              <button onClick={zoomOut} className="rounded bg-gray-700 px-2 py-1 text-xs font-medium text-gray-200 hover:bg-gray-600 disabled:opacity-40" title="Zoom out (-)" disabled={viewerMode === "zoom" && zoom <= MIN_ZOOM}>-</button>
              <span className="w-12 text-center text-xs tabular-nums text-gray-300">{zoomLabel}</span>
              <button onClick={zoomIn} className="rounded bg-gray-700 px-2 py-1 text-xs font-medium text-gray-200 hover:bg-gray-600 disabled:opacity-40" title="Zoom in (+)" disabled={viewerMode === "zoom" && zoom >= MAX_ZOOM}>+</button>
            </div>
          </div>
        </div>

        {/* Analysis panel */}
        <div className="h-56 w-full flex-shrink-0 overflow-y-auto border-t border-gray-700 bg-gray-800 sm:h-64 xl:h-auto xl:w-80 xl:border-l xl:border-t-0">
          <div className="p-4">
            {/* Scene summary */}
            {currentFrame!.scene_summary && (
              <div className="mb-4">
                <h5 className="mb-1 text-xs font-medium uppercase text-gray-400">Scene Summary</h5>
                <p className="text-sm text-gray-200">{currentFrame!.scene_summary}</p>
              </div>
            )}

            {/* Detection toggles */}
            <DetectionToggleList
              detections={currentFrame!.detections}
              visibleIndices={visibleDetections}
              onToggle={handleToggleDetection}
              onShowAll={handleShowAll}
              onHideAll={handleHideAll}
            />

            {/* QA pairs */}
            {currentFrame!.qa && currentFrame!.qa.length > 0 && (
              <div className="mt-4">
                <h5 className="mb-2 text-xs font-medium uppercase text-gray-400">Q&A</h5>
                <div className="space-y-2">
                  {currentFrame!.qa.map((qa, idx) => (
                    <div key={idx} className="rounded bg-gray-700 p-2 text-xs">
                      <p className="font-medium text-gray-300">{qa.q}</p>
                      <p className="mt-1 text-gray-400">{qa.a}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Site summary */}
            {counts?.summary && (
              <div className="mt-4 border-t border-gray-700 pt-4">
                <h5 className="mb-2 text-xs font-medium uppercase text-gray-400">Site Summary</h5>
                <div className="space-y-1.5 text-xs">
                  <div className="flex justify-between text-gray-300">
                    <span>Peak Persons</span>
                    <span className="font-mono">{counts.summary.peak_persons}</span>
                  </div>
                  <div className="flex justify-between text-gray-300">
                    <span>Avg Persons</span>
                    <span className="font-mono">{typeof counts.summary.avg_persons === "number" ? counts.summary.avg_persons.toFixed(1) : counts.summary.avg_persons}</span>
                  </div>
                  {Object.entries(counts.summary.peak_equipment || {}).map(([key, val]) => (
                    <div key={key} className="flex justify-between text-gray-300">
                      <span>Peak {key.replace(/_/g, " ")}</span>
                      <span className="font-mono">{val as number}</span>
                    </div>
                  ))}
                  {Object.entries(counts.summary.peak_hardhats || {}).map(([key, val]) => (
                    <div key={key} className="flex justify-between text-gray-300">
                      <span>Peak {key} hardhats</span>
                      <span className="font-mono">{val as number}</span>
                    </div>
                  ))}
                  <div className="flex justify-between text-gray-400">
                    <span>Total Frames</span>
                    <span className="font-mono">{counts.summary.total_frames}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Engine info */}
            {currentFrame!.engine && (
              <div className="mt-4 border-t border-gray-700 pt-3 text-xs text-gray-500">
                <p>Engine: {currentFrame!.engine.name}</p>
                <p>Provider: {currentFrame!.engine.provider}</p>
                <p>Model: {currentFrame!.engine.model}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
