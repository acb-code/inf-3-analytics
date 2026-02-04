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
  commentCount?: number;
  onClick: () => void;
  onViewFrames?: () => void;
  onDelete?: () => void;
  onViewComments?: () => void;
}

export function EventCard({
  event,
  isActive,
  hasFrames,
  commentCount,
  onClick,
  onViewFrames,
  onDelete,
  onViewComments,
}: EventCardProps) {
  const isManual = event.metadata?.source === "manual";

  return (
    <div
      className={`group rounded-lg border p-3 transition-all ${
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
        {isManual && (
          <span className="rounded border border-purple-200 bg-purple-50 px-1.5 py-0.5 text-xs font-medium text-purple-700">
            Manual
          </span>
        )}
        {/* Delete button - shows on hover */}
        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="ml-auto rounded p-0.5 text-gray-400 opacity-0 transition-opacity hover:bg-red-100 hover:text-red-600 group-hover:opacity-100"
            title="Delete event"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
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
        {onViewComments && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onViewComments();
            }}
            className="flex items-center gap-1 rounded bg-gray-100 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-200"
          >
            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
            </svg>
            {commentCount !== undefined && commentCount > 0 && (
              <span className="rounded-full bg-blue-600 px-1.5 text-[10px] text-white">
                {commentCount}
              </span>
            )}
          </button>
        )}
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
            Frames
          </button>
        )}
      </div>
    </div>
  );
}
