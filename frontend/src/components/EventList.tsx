"use client";

import { useRef, useEffect } from "react";
import type { Event } from "@/types/api";
import { EventCard } from "./EventCard";

interface EventListProps {
  events: Event[];
  currentTime: number;
  onEventClick: (event: Event) => void;
}

export function EventList({ events, currentTime, onEventClick }: EventListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLDivElement>(null);

  // Find the active event based on current video time
  const activeEventId = events.find(
    (e) => currentTime >= e.start_s && currentTime <= e.end_s
  )?.event_id;

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
          return (
            <div key={event.event_id} ref={isActive ? activeRef : undefined}>
              <EventCard
                event={event}
                isActive={isActive}
                onClick={() => onEventClick(event)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
