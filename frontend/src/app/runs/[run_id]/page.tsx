"use client";

import { useEffect, useState, useRef, use, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { RunDetailResponse, Event, EventFrameSet, PipelineStatusResponse, PipelineStep, CreateEventRequest, TriggerPipelineRequest } from "@/types/api";
import { VideoPlayer } from "@/components/VideoPlayer";
import { EventList } from "@/components/EventList";
import { EventFrameViewer } from "@/components/EventFrameViewer";
import { SiteAnalyticsViewer } from "@/components/SiteAnalyticsViewer";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { PipelineStatus } from "@/components/PipelineStatus";
import { AddEventModal } from "@/components/AddEventModal";
import { EventComments } from "@/components/EventComments";
import { useLanguage } from "@/lib/i18n";

interface PageProps {
  params: Promise<{ run_id: string }>;
}


// Event-based pipeline steps (run with "Run All Steps")
const EVENT_STEP_ORDER: PipelineStep[] = [
  "transcribe",
  "extract_events",
  "extract_frames",
  "frame_analytics",
];

// Dependency map for step prerequisites
const STEP_PREREQUISITES: Record<PipelineStep, PipelineStep[]> = {
  transcribe: [],
  extract_events: ["transcribe"],
  extract_frames: ["extract_events"],
  frame_analytics: ["extract_frames"],
  site_analytics: [], // Independent — only needs video
};

const SITE_ENGINE_OPTIONS = [
  { value: "openai", label: "OpenAI" },
  { value: "gemini", label: "Gemini" },
  { value: "yolo", label: "YOLO" },
];

const FRAME_ENGINE_OPTIONS = [
  { value: "openai", label: "OpenAI" },
  { value: "gemini", label: "Gemini" },
];

const CAPABILITY_KEYS = [
  { name: "cap.transcription.name", desc: "cap.transcription.desc" },
  { name: "cap.events.name", desc: "cap.events.desc" },
  { name: "cap.frames.name", desc: "cap.frames.desc" },
  { name: "cap.frameAnalytics.name", desc: "cap.frameAnalytics.desc" },
  { name: "cap.siteAnalytics.name", desc: "cap.siteAnalytics.desc" },
] as const;

export default function RunDetailPage({ params }: PageProps) {
  const { run_id } = use(params);
  const { lang, setLang, t } = useLanguage();
  const [runDetail, setRunDetail] = useState<RunDetailResponse | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [eventFrameSets, setEventFrameSets] = useState<EventFrameSet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [selectedFrameSet, setSelectedFrameSet] = useState<EventFrameSet | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusResponse | null>(null);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [activeTab, setActiveTab] = useState<"pipeline" | "site_analytics">("pipeline");
  const [showCapabilities, setShowCapabilities] = useState(true);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showAddEventModal, setShowAddEventModal] = useState(false);
  const [selectedEventForComments, setSelectedEventForComments] = useState<Event | null>(null);
  const [commentCounts, setCommentCounts] = useState<Record<string, number>>({});
  const [videoDuration, setVideoDuration] = useState<number | undefined>(undefined);
  const [showSiteAnalytics, setShowSiteAnalytics] = useState(false);
  const [siteEngine, setSiteEngine] = useState("openai");
  const [frameEngine, setFrameEngine] = useState("openai");
  const [analyzingEventId, setAnalyzingEventId] = useState<string | null>(null);
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
      await api.startPipeline(run_id, {
        frame_analytics_engine: frameEngine,
        language: lang,
      });
      setShowAnalytics(true);
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

  const handleRunStep = async (step: PipelineStep, request?: TriggerPipelineRequest) => {
    setActionError(null);
    try {
      await api.runPipelineStep(run_id, step, request);
      setShowAnalytics(true);
    } catch (err) {
      setActionError((err as Error).message);
    }
  };

  const handleRunSiteAnalytics = async () => {
    await handleRunStep("site_analytics", {
      site_analytics_engine: siteEngine,
      language: lang,
    });
  };

  const handlePipelineComplete = useCallback(() => {
    fetchData();
  }, [fetchData]);

  const handlePipelineStatusUpdate = useCallback((status: PipelineStatusResponse) => {
    setPipelineStatus(status);
  }, []);

  const handleAddEvent = () => {
    setShowAddEventModal(true);
  };

  const handleCreateEvent = async (request: CreateEventRequest) => {
    await api.createEvent(run_id, request);
    const eventsData = await api.getEvents(run_id).catch(() => ({ events: [] }));
    setEvents(eventsData.events || []);
  };

  const handleAnalyzeEvent = async (event: Event) => {
    setActionError(null);
    setAnalyzingEventId(event.event_id);
    try {
      await api.runPipelineStep(run_id, "frame_analytics", {
        frame_analytics_engine: frameEngine,
        event_id: event.event_id,
        language: lang,
      });
      setShowAnalytics(true);
    } catch (err) {
      setActionError((err as Error).message);
    } finally {
      setAnalyzingEventId(null);
    }
  };

  const handleUpdateEventSeverity = async (event: Event, severity: string | null) => {
    setActionError(null);
    try {
      const updated = await api.updateEvent(run_id, event.event_id, { severity });
      setEvents((prev) => prev.map((e) => (e.event_id === event.event_id ? updated : e)));
    } catch (err) {
      setActionError((err as Error).message);
    }
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
    const prereqs = STEP_PREREQUISITES[step] || [];
    if (prereqs.length === 0) return true;
    if (!pipelineStatus) return false;

    return prereqs.every((prereq) => {
      const prereqStatus = pipelineStatus.steps.find((s) => s.step === prereq);
      return prereqStatus && (prereqStatus.status === "completed" || prereqStatus.status === "skipped");
    });
  };

  const isSiteAnalyticsCompleted = pipelineStatus?.steps.find(
    (s) => s.step === "site_analytics"
  )?.status === "completed";

  const hasSiteAnalyticsArtifact = runDetail?.artifacts.some(
    (a) => a.type === "site_analytics" && a.available
  ) ?? false;

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
          <p className="font-medium">{t("detail.errorLoading")}</p>
          <p className="text-sm">{error || t("detail.notFound")}</p>
          <Link href="/runs" className="mt-2 inline-block text-sm underline">
            {t("detail.backToRuns")}
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
            <Link href="/runs" className="text-gray-600 hover:text-gray-900">
              &larr; {t("detail.runs")}
            </Link>
            <div className="min-w-0">
              <h1 className="break-all font-mono text-lg font-medium text-gray-900">
                {run.run_id}
              </h1>
              <p className="break-words text-sm text-gray-500">{run.video_basename}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="inline-flex rounded border border-gray-300 text-sm"
              title="Analysis and prompt language"
            >
              <button
                onClick={() => setLang("en")}
                className={`px-2 py-1 ${lang === "en" ? "bg-blue-600 text-white" : "bg-white text-gray-700 hover:bg-gray-50"}`}
              >
                EN
              </button>
              <button
                onClick={() => setLang("fr")}
                className={`px-2 py-1 ${lang === "fr" ? "bg-blue-600 text-white" : "bg-white text-gray-700 hover:bg-gray-50"}`}
              >
                FR
              </button>
            </div>
            {(hasSiteAnalyticsArtifact || isSiteAnalyticsCompleted) && (
              <button
                onClick={() => setShowSiteAnalytics(true)}
                className="rounded border border-green-300 bg-green-50 px-3 py-1.5 text-sm font-medium text-green-700 hover:bg-green-100"
              >
                {t("detail.viewSiteAnalytics")}
              </button>
            )}
            <button
              onClick={() => setShowAnalytics(!showAnalytics)}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              {showAnalytics ? t("detail.hideAnalytics") : t("detail.showAnalytics")}
            </button>
          </div>
        </div>
      </header>

      {/* Capabilities overview */}
      <div className="border-b border-gray-100 bg-blue-50/50 px-4 py-2">
        <button
          onClick={() => setShowCapabilities(!showCapabilities)}
          className="flex w-full items-center gap-1 text-left text-xs font-medium text-blue-700 hover:text-blue-900"
        >
          <svg
            className={`h-3.5 w-3.5 transition-transform ${showCapabilities ? "rotate-90" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          {t("detail.whatsAvailable")}
        </button>
        {showCapabilities && (
          <div className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2 lg:grid-cols-5">
            {CAPABILITY_KEYS.map((cap) => (
              <div key={cap.name} className="py-1">
                <span className="text-xs font-semibold text-gray-700">{t(cap.name)}</span>
                <p className="text-xs text-gray-500">{t(cap.desc)}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Analytics panel with tabs */}
      {showAnalytics && (
        <div className="border-b border-gray-200 bg-gray-50">
          {/* Tab bar */}
          <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4">
            <div className="flex">
              <button
                onClick={() => setActiveTab("pipeline")}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === "pipeline"
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {t("detail.pipeline")}
              </button>
              <button
                onClick={() => setActiveTab("site_analytics")}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === "site_analytics"
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {t("detail.siteAnalytics")}
              </button>
            </div>
          </div>

          <div className="p-4">
            <div className="mx-auto max-w-4xl">
              {/* Event Pipeline tab */}
              {activeTab === "pipeline" && (
                <>
                  <div className="mb-4 flex flex-wrap items-center gap-2">
                    {EVENT_STEP_ORDER.map((step) => (
                      <button
                        key={step}
                        title={t(`tooltip.${step}` as Parameters<typeof t>[0])}
                        onClick={() => handleRunStep(step, {
                          ...(step === "frame_analytics" ? { frame_analytics_engine: frameEngine } : {}),
                          language: lang,
                        })}
                        disabled={!isStepEnabled(step) || isAnyStepRunning}
                        className={`rounded px-3 py-1.5 text-sm ${
                          !isStepEnabled(step) || isAnyStepRunning
                            ? "cursor-not-allowed bg-gray-200 text-gray-500"
                            : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
                        }`}
                      >
                        {t(`step.${step}` as Parameters<typeof t>[0])}
                      </button>
                    ))}

                    {/* Frame engine selector */}
                    <div className="flex flex-col">
                      <select
                        value={frameEngine}
                        onChange={(e) => setFrameEngine(e.target.value)}
                        className="rounded border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-700"
                      >
                        {FRAME_ENGINE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                      <span className="mt-0.5 text-xs text-gray-400">{t("detail.vlmEngine")}</span>
                    </div>

                    <div className="mx-1 h-6 w-px bg-gray-300" />

                    {/* Run All / Cancel */}
                    {isAnyStepRunning ? (
                      <button
                        onClick={handleCancelPipeline}
                        className="rounded bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
                      >
                        {t("detail.cancelPipeline")}
                      </button>
                    ) : (
                      <button
                        onClick={handleStartPipeline}
                        title="Run transcribe, extract events, extract frames, and frame analytics in sequence"
                        className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
                      >
                        {t("detail.runAll")}
                      </button>
                    )}
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
                    filterSteps={EVENT_STEP_ORDER}
                  />
                </>
              )}

              {/* Site Analytics tab */}
              {activeTab === "site_analytics" && (
                <>
                  <div className="mb-4 flex flex-wrap items-center gap-2">
                    <button
                      onClick={handleRunSiteAnalytics}
                      title={t("tooltip.site_analytics")}
                      disabled={isAnyStepRunning}
                      className={`rounded px-3 py-1.5 text-sm ${
                        isAnyStepRunning
                          ? "cursor-not-allowed bg-gray-200 text-gray-500"
                          : "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50"
                      }`}
                    >
                      {t("detail.runSiteAnalytics")}
                    </button>

                    {/* Site engine selector */}
                    <div className="flex flex-col">
                      <select
                        value={siteEngine}
                        onChange={(e) => setSiteEngine(e.target.value)}
                        className="rounded border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-700"
                      >
                        {SITE_ENGINE_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                      <span className="mt-0.5 text-xs text-gray-400">{t("detail.detectionEngine")}</span>
                    </div>

                    {/* View Site Analytics button (when completed) */}
                    {(isSiteAnalyticsCompleted || hasSiteAnalyticsArtifact) && (
                      <button
                        onClick={() => setShowSiteAnalytics(true)}
                        className="rounded bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700"
                      >
                        {t("detail.viewSiteAnalytics")}
                      </button>
                    )}
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
                    filterSteps={["site_analytics"]}
                  />
                </>
              )}
            </div>
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
              {t("detail.events")} ({events.length})
            </h2>
          </div>
          <div className="flex-1 overflow-hidden">
            <EventList
              events={events}
              currentTime={currentTime}
              eventFrameSets={eventFrameSets}
              commentCounts={commentCounts}
              analyzingEventId={analyzingEventId}
              onEventClick={handleEventClick}
              onViewFrames={handleViewFrames}
              onAddEvent={handleAddEvent}
              onDeleteEvent={handleDeleteEvent}
              onViewComments={handleViewComments}
              onAnalyzeEvent={handleAnalyzeEvent}
              onUpdateSeverity={handleUpdateEventSeverity}
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

      {/* Site analytics viewer modal */}
      {showSiteAnalytics && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
          <div className="h-[95vh] w-[98vw] max-w-7xl overflow-hidden rounded-lg sm:h-[90vh] sm:w-[95vw]">
            <SiteAnalyticsViewer
              runId={run_id}
              language={lang}
              onClose={() => setShowSiteAnalytics(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
