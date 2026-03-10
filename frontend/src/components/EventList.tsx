"use client";

import { useRef, useEffect } from "react";
import type { Event, EventFrameSet } from "@/types/api";
import { EventCard } from "./EventCard";
import { useLanguage } from "@/lib/i18n";

interface EventListProps {
  events: Event[];
  currentTime: number;
  eventFrameSets?: EventFrameSet[];
  commentCounts?: Record<string, number>;
  analyzingEventId?: string | null;
  onEventClick: (event: Event) => void;
  onViewFrames?: (event: Event, frameSet: EventFrameSet) => void;
  onAddEvent?: () => void;
  onDeleteEvent?: (event: Event) => void;
  onViewComments?: (event: Event) => void;
  onAnalyzeEvent?: (event: Event) => void;
  onUpdateSeverity?: (event: Event, severity: string | null) => void;
}

export function EventList({
  events,
  currentTime,
  eventFrameSets,
  commentCounts,
  analyzingEventId,
  onEventClick,
  onViewFrames,
  onAddEvent,
  onDeleteEvent,
  onViewComments,
  onAnalyzeEvent,
  onUpdateSeverity,
}: EventListProps) {
  const { t } = useLanguage();
  const containerRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLDivElement>(null);

  // Find the active event based on current video time
  const activeEventId = events.find(
    (e) => currentTime >= e.start_s && currentTime <= e.end_s
  )?.event_id;

  // Create a map of event_id to frame set for quick lookup
  const frameSetMap = new Map<string, EventFrameSet>();
  if (eventFrameSets) {
    for (const fs of eventFrameSets) {
      frameSetMap.set(fs.event_id, fs);
    }
  }

  // Helper to find matching frame set by time range (fallback)
  const findFrameSetForEvent = (event: Event): EventFrameSet | undefined => {
    // First try exact event_id match
    const exactMatch = frameSetMap.get(event.event_id);
    if (exactMatch) return exactMatch;

    // Fallback: match by overlapping time range
    if (eventFrameSets) {
      return eventFrameSets.find(
        (fs) =>
          Math.abs(fs.start_s - event.start_s) < 0.5 &&
          Math.abs(fs.end_s - event.end_s) < 0.5
      );
    }
    return undefined;
  };

  // Auto-scroll to active event
  useEffect(() => {
    if (activeRef.current && containerRef.current) {
      const container = containerRef.current;
      const element = activeRef.current;
      const containerRect = container.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();

      // Only scroll if element is outside visible area
      if (
        elementRect.top < containerRect.top ||
        elementRect.bottom > containerRect.bottom
      ) {
        element.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [activeEventId]);

  if (events.length === 0) {
    return (
      <div className="flex h-full flex-col">
        {onAddEvent && (
          <div className="border-b border-gray-200 p-2">
            <button
              onClick={onAddEvent}
              className="flex w-full items-center justify-center gap-1 rounded border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-600 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              {t("events.addManualEvent")}
            </button>
          </div>
        )}
        <div className="flex flex-1 items-center justify-center text-gray-500">
          {t("events.noEvents")}
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="h-full overflow-y-auto">
      <div className="space-y-2 p-2">
        {onAddEvent && (
          <button
            onClick={onAddEvent}
            className="flex w-full items-center justify-center gap-1 rounded border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-600 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            {t("events.addManualEvent")}
          </button>
        )}
        {events.map((event) => {
          const isActive = event.event_id === activeEventId;
          const frameSet = findFrameSetForEvent(event);
          return (
            <div key={event.event_id} ref={isActive ? activeRef : undefined}>
              <EventCard
                event={event}
                isActive={isActive}
                hasFrames={!!frameSet && frameSet.frames.length > 0}
                commentCount={commentCounts?.[event.event_id]}
                isAnalyzing={analyzingEventId === event.event_id}
                onClick={() => onEventClick(event)}
                onViewFrames={
                  frameSet && onViewFrames
                    ? () => onViewFrames(event, frameSet)
                    : undefined
                }
                onDelete={onDeleteEvent ? () => onDeleteEvent(event) : undefined}
                onViewComments={onViewComments ? () => onViewComments(event) : undefined}
                onAnalyzeEvent={onAnalyzeEvent ? () => onAnalyzeEvent(event) : undefined}
                onUpdateSeverity={onUpdateSeverity ? (sev) => onUpdateSeverity(event, sev) : undefined}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
