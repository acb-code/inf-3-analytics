"use client";

import { useRef, useEffect } from "react";
import type { Event, EventFrameSet } from "@/types/api";
import { EventCard } from "./EventCard";

interface EventListProps {
  events: Event[];
  currentTime: number;
  eventFrameSets?: EventFrameSet[];
  onEventClick: (event: Event) => void;
  onViewFrames?: (event: Event, frameSet: EventFrameSet) => void;
}

export function EventList({
  events,
  currentTime,
  eventFrameSets,
  onEventClick,
  onViewFrames,
}: EventListProps) {
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
      <div className="flex h-full items-center justify-center text-gray-500">
        No events found
      </div>
    );
  }

  return (
    <div ref={containerRef} className="h-full overflow-y-auto">
      <div className="space-y-2 p-2">
        {events.map((event) => {
          const isActive = event.event_id === activeEventId;
          const frameSet = findFrameSetForEvent(event);
          return (
            <div key={event.event_id} ref={isActive ? activeRef : undefined}>
              <EventCard
                event={event}
                isActive={isActive}
                hasFrames={!!frameSet && frameSet.frames.length > 0}
                onClick={() => onEventClick(event)}
                onViewFrames={
                  frameSet && onViewFrames
                    ? () => onViewFrames(event, frameSet)
                    : undefined
                }
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
