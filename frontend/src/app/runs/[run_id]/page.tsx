"use client";

import { useEffect, useState, useRef, use } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { RunDetailResponse, Event, EventFrameSet } from "@/types/api";
import { VideoPlayer } from "@/components/VideoPlayer";
import { EventList } from "@/components/EventList";
import { EventFrameViewer } from "@/components/EventFrameViewer";
import { LoadingSpinner } from "@/components/LoadingSpinner";

interface PageProps {
  params: Promise<{ run_id: string }>;
}

export default function RunDetailPage({ params }: PageProps) {
  const { run_id } = use(params);
  const [runDetail, setRunDetail] = useState<RunDetailResponse | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [eventFrameSets, setEventFrameSets] = useState<EventFrameSet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [selectedFrameSet, setSelectedFrameSet] = useState<EventFrameSet | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api.getRun(run_id, { signal: controller.signal }),
      api.getEvents(run_id, { signal: controller.signal }).catch(() => ({ events: [] })),
      api
        .getEventFramesManifest(run_id, { signal: controller.signal })
        .catch(() => ({ event_frame_sets: [] })),
    ])
      .then(([runData, eventsData, framesManifest]) => {
        setRunDetail(runData);
        setEvents(eventsData.events || []);
        setEventFrameSets(framesManifest.event_frame_sets || []);
        setLoading(false);
      })
      .catch((err) => {
        if (err?.name === "AbortError") return;
        setError(err.message);
        setLoading(false);
      });
    return () => controller.abort();
  }, [run_id]);

  const handleEventClick = (event: Event) => {
    if (videoRef.current) {
      videoRef.current.currentTime = event.start_s;
      videoRef.current.play();
    }
  };

  const handleViewFrames = (_event: Event, frameSet: EventFrameSet) => {
    setSelectedFrameSet(frameSet);
  };

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
        <div className="flex items-center gap-4">
          <Link
            href="/runs"
            className="text-gray-600 hover:text-gray-900"
          >
            &larr; Runs
          </Link>
          <div>
            <h1 className="font-mono text-lg font-medium text-gray-900">
              {run.run_id}
            </h1>
            <p className="text-sm text-gray-500">{run.video_basename}</p>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden lg:flex-row">
        {/* Video section - 2/3 width on desktop */}
        <div className="h-[50vh] lg:h-auto lg:flex-1 bg-gray-900 p-4 lg:w-2/3">
          <VideoPlayer
            ref={videoRef}
            src={api.getVideoUrl(run_id)}
            onTimeUpdate={setCurrentTime}
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
              onEventClick={handleEventClick}
              onViewFrames={handleViewFrames}
            />
          </div>
        </div>
      </div>

      {/* Frame viewer modal */}
      {selectedFrameSet && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
          <div className="h-[90vh] w-[95vw] max-w-7xl overflow-hidden rounded-lg">
            <EventFrameViewer
              runId={run_id}
              eventFrameSet={selectedFrameSet}
              onClose={() => setSelectedFrameSet(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
