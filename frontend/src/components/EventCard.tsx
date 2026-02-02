import type { Event } from "@/types/api";
import {
  formatTime,
  getSeverityColor,
  getEventTypeColor,
  formatEventType,
} from "@/lib/format";

interface EventCardProps {
  event: Event;
  isActive: boolean;
  onClick: () => void;
}

export function EventCard({ event, isActive, onClick }: EventCardProps) {
  return (
    <button
      onClick={onClick}
      className={`w-full rounded-lg border p-3 text-left transition-all ${
        isActive
          ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200"
          : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50"
      }`}
    >
      {/* Time and badges */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-gray-600">
          {formatTime(event.start_s)} - {formatTime(event.end_s)}
        </span>
        <span
          className={`rounded border px-1.5 py-0.5 text-xs font-medium capitalize ${getEventTypeColor(event.event_type)}`}
        >
          {formatEventType(event.event_type)}
        </span>
        {event.severity && (
          <span
            className={`rounded border px-1.5 py-0.5 text-xs font-medium capitalize ${getSeverityColor(event.severity)}`}
          >
            {event.severity}
          </span>
        )}
      </div>

      {/* Title */}
      <h4 className="mb-1 text-sm font-medium text-gray-900">{event.title}</h4>

      {/* Summary */}
      <p className="mb-2 text-xs text-gray-600 line-clamp-2">{event.summary}</p>

      {/* Transcript excerpt */}
      {event.transcript_ref?.excerpt && (
        <p className="border-l-2 border-gray-300 pl-2 text-xs italic text-gray-500 line-clamp-2">
          "{event.transcript_ref.excerpt}"
        </p>
      )}
    </button>
  );
}
