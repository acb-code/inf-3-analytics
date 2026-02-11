"use client";

import { useEffect, useState, useRef, use, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { RunDetailResponse, Event, EventFrameSet, PipelineStatusResponse, PipelineStep, CreateEventRequest } from "@/types/api";
import { VideoPlayer } from "@/components/VideoPlayer";
import { EventList } from "@/components/EventList";
import { EventFrameViewer } from "@/components/EventFrameViewer";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { PipelineStatus } from "@/components/PipelineStatus";
import { AddEventModal } from "@/components/AddEventModal";
import { EventComments } from "@/components/EventComments";

interface PageProps {
  params: Promise<{ run_id: string }>;
}

const STEP_LABELS: Record<PipelineStep, string> = {
  transcribe: "Transcribe",
  extract_events: "Extract Events",
  extract_frames: "Extract Frames",
  frame_analytics: "Analyze Frames",
};

const STEP_ORDER: PipelineStep[] = [
  "transcribe",
  "extract_events",
  "extract_frames",
  "frame_analytics",
];

export default function RunDetailPage({ params }: PageProps) {
  const { run_id } = use(params);
  const [runDetail, setRunDetail] = useState<RunDetailResponse | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [eventFrameSets, setEventFrameSets] = useState<EventFrameSet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [selectedFrameSet, setSelectedFrameSet] = useState<EventFrameSet | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusResponse | null>(null);
  const [showPipeline, setShowPipeline] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showAddEventModal, setShowAddEventModal] = useState(false);
  const [selectedEventForComments, setSelectedEventForComments] = useState<Event | null>(null);
  const [commentCounts, setCommentCounts] = useState<Record<string, number>>({});
  const [videoDuration, setVideoDuration] = useState<number | undefined>(undefined);
  const videoRef = useRef<HTMLVideoElement>(null);

  const fetchData = useCallback(async (signal?: AbortSignal) => {
    try {
      const [runData, eventsData, framesManifest, pipelineData] = await Promise.all([
        api.getRun(run_id, { signal }),
        api.getEvents(run_id, { signal }).catch(() => ({ events: [] })),
        api.getEventFramesManifest(run_id, { signal }).catch(() => ({ event_frame_sets: [] })),
        api.getPipelineStatus(run_id, { signal }).catch(() => null),
      ]);
      setRunDetail(runData);
      setEvents(eventsData.events || []);
      setEventFrameSets(framesManifest.event_frame_sets || []);
      setPipelineStatus(pipelineData);
      setLoading(false);
    } catch (err) {
      if ((err as Error)?.name === "AbortError") return;
      setError((err as Error).message);
      setLoading(false);
    }
  }, [run_id]);

  useEffect(() => {
    const controller = new AbortController();
    fetchData(controller.signal);
    return () => controller.abort();
  }, [fetchData]);

  const handleEventClick = (event: Event) => {
    if (videoRef.current) {
      videoRef.current.currentTime = event.start_s;
      videoRef.current.play();
    }
  };

  const handleViewFrames = (_event: Event, frameSet: EventFrameSet) => {
    setSelectedFrameSet(frameSet);
  };

  const handleStartPipeline = async () => {
    setActionError(null);
    try {
      await api.startPipeline(run_id);
      setShowPipeline(true);
    } catch (err) {
      setActionError((err as Error).message);
    }
  };

  const handleCancelPipeline = async () => {
    setActionError(null);
    try {
      await api.cancelPipeline(run_id);
    } catch (err) {
      setActionError((err as Error).message);
    }
  };

  const handleRunStep = async (step: PipelineStep) => {
    setActionError(null);
    try {
      await api.runPipelineStep(run_id, step);
      setShowPipeline(true);
    } catch (err) {
      setActionError((err as Error).message);
    }
  };

  const handlePipelineComplete = () => {
    // Refresh data after pipeline completes
    fetchData();
  };

  const handlePipelineStatusUpdate = useCallback((status: PipelineStatusResponse) => {
    setPipelineStatus(status);
  }, []);

  const handleAddEvent = () => {
    setShowAddEventModal(true);
  };

  const handleCreateEvent = async (request: CreateEventRequest) => {
    await api.createEvent(run_id, request);
    // Refresh events
    const eventsData = await api.getEvents(run_id).catch(() => ({ events: [] }));
    setEvents(eventsData.events || []);
  };

  const handleDeleteEvent = async (event: Event) => {
    if (!confirm(`Delete event "${event.title}"?`)) return;
    try {
      await api.deleteEvent(run_id, event.event_id);
      setEvents(events.filter((e) => e.event_id !== event.event_id));
    } catch (err) {
      setActionError((err as Error).message);
    }
  };

  const handleViewComments = (event: Event) => {
    setSelectedEventForComments(event);
  };

  const handleVideoDuration = (duration: number) => {
    setVideoDuration(duration);
  };

  const isStepEnabled = (step: PipelineStep): boolean => {
    if (!pipelineStatus) return step === "transcribe";
    const stepIndex = STEP_ORDER.indexOf(step);
    if (stepIndex === 0) return true;

    // Check if all previous steps are completed
    for (let i = 0; i < stepIndex; i++) {
      const prevStep = STEP_ORDER[i];
      const prevStatus = pipelineStatus.steps.find((s) => s.step === prevStep);
      if (!prevStatus || (prevStatus.status !== "completed" && prevStatus.status !== "skipped")) {
        return false;
      }
    }
    return true;
  };

  const isAnyStepRunning = pipelineStatus?.steps.some((s) => s.status === "running") ?? false;

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (error || !runDetail) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <p className="font-medium">Error loading run</p>
          <p className="text-sm">{error || "Run not found"}</p>
          <Link href="/runs" className="mt-2 inline-block text-sm underline">
            Back to runs
          </Link>
        </div>
      </div>
    );
  }

  const { run } = runDetail;

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex min-w-0 items-center gap-4">
            <Link
              href="/runs"
              className="text-gray-600 hover:text-gray-900"
            >
              &larr; Runs
            </Link>
            <div className="min-w-0">
              <h1 className="break-all font-mono text-lg font-medium text-gray-900">
                {run.run_id}
              </h1>
              <p className="break-words text-sm text-gray-500">{run.video_basename}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowPipeline(!showPipeline)}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              {showPipeline ? "Hide Pipeline" : "Show Pipeline"}
            </button>
            {isAnyStepRunning ? (
              <button
                onClick={handleCancelPipeline}
                className="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
              >
                Cancel Pipeline
              </button>
            ) : (
              <button
                onClick={handleStartPipeline}
                className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
              >
                Run All Steps
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Pipeline panel */}
      {showPipeline && (
        <div className="border-b border-gray-200 bg-gray-50 p-4">
          <div className="mx-auto max-w-4xl">
            <div className="mb-4 flex flex-wrap gap-2">
              {STEP_ORDER.map((step) => (
                <button
                  key={step}
                  onClick={() => handleRunStep(step)}
                  disabled={!isStepEnabled(step) || isAnyStepRunning}
                  className={`rounded px-3 py-1.5 text-sm ${
                    !isStepEnabled(step) || isAnyStepRunning
                      ? "cursor-not-allowed bg-gray-200 text-gray-500"
                      : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {STEP_LABELS[step]}
                </button>
              ))}
            </div>
            {actionError && (
              <div className="mb-4 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">
                {actionError}
              </div>
            )}
            <PipelineStatus
              runId={run_id}
              onComplete={handlePipelineComplete}
              onStatusUpdate={handlePipelineStatusUpdate}
            />
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden lg:flex-row">
        {/* Video section - 2/3 width on desktop */}
        <div className="min-h-[200px] h-[50vh] lg:h-auto lg:flex-1 bg-gray-900 p-2 sm:p-4 lg:w-2/3">
          <VideoPlayer
            ref={videoRef}
            src={api.getVideoUrl(run_id)}
            onTimeUpdate={setCurrentTime}
            onDurationChange={handleVideoDuration}
          />
        </div>

        {/* Events section - 1/3 width on desktop */}
        <div className="flex min-h-0 flex-1 flex-col border-l border-gray-200 bg-gray-50 lg:w-1/3">
          <div className="border-b border-gray-200 bg-white px-4 py-3">
            <h2 className="font-medium text-gray-900">
              Events ({events.length})
            </h2>
          </div>
          <div className="flex-1 overflow-hidden">
            <EventList
              events={events}
              currentTime={currentTime}
              eventFrameSets={eventFrameSets}
              commentCounts={commentCounts}
              onEventClick={handleEventClick}
              onViewFrames={handleViewFrames}
              onAddEvent={handleAddEvent}
              onDeleteEvent={handleDeleteEvent}
              onViewComments={handleViewComments}
            />
          </div>
        </div>
      </div>

      {/* Frame viewer modal */}
      {selectedFrameSet && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
          <div className="h-[95vh] w-[98vw] max-w-7xl overflow-hidden rounded-lg sm:h-[90vh] sm:w-[95vw]">
            <EventFrameViewer
              runId={run_id}
              eventFrameSet={selectedFrameSet}
              onClose={() => setSelectedFrameSet(null)}
            />
          </div>
        </div>
      )}

      {/* Add event modal */}
      {showAddEventModal && (
        <AddEventModal
          currentTime={currentTime}
          videoDuration={videoDuration}
          onSubmit={handleCreateEvent}
          onClose={() => setShowAddEventModal(false)}
        />
      )}

      {/* Comments modal */}
      {selectedEventForComments && (
        <EventComments
          runId={run_id}
          event={selectedEventForComments}
          onClose={() => setSelectedEventForComments(null)}
        />
      )}
    </div>
  );
}
