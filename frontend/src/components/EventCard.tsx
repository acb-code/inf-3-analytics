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
  hasFrames?: boolean;
  onClick: () => void;
  onViewFrames?: () => void;
}

export function EventCard({
  event,
  isActive,
  hasFrames,
  onClick,
  onViewFrames,
}: EventCardProps) {
  return (
    <div
      className={`rounded-lg border p-3 transition-all ${
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

      {/* Action buttons */}
      <div className="mt-2 flex gap-2">
        <button
          onClick={onClick}
          className="flex-1 rounded bg-gray-100 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-200"
        >
          Go to time
        </button>
        {hasFrames && onViewFrames && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onViewFrames();
            }}
            className="flex items-center gap-1 rounded bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-200"
          >
            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            View Frames
          </button>
        )}
      </div>
    </div>
  );
}
