"use client";

import { useState } from "react";
import type { EventType, Severity, CreateEventRequest } from "@/types/api";
import { formatTime } from "@/lib/format";

const EVENT_TYPES: { value: EventType; label: string }[] = [
  { value: "observation", label: "Observation" },
  { value: "structural_anomaly", label: "Structural Anomaly" },
  { value: "maintenance_note", label: "Maintenance Note" },
  { value: "safety_risk", label: "Safety Risk" },
  { value: "measurement", label: "Measurement" },
  { value: "location_reference", label: "Location Reference" },
  { value: "uncertainty", label: "Uncertainty" },
  { value: "other", label: "Other" },
];

const SEVERITIES: { value: Severity; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

interface AddEventModalProps {
  currentTime: number;
  videoDuration?: number;
  onSubmit: (request: CreateEventRequest) => Promise<void>;
  onClose: () => void;
}

export function AddEventModal({
  currentTime,
  videoDuration,
  onSubmit,
  onClose,
}: AddEventModalProps) {
  const [startS, setStartS] = useState(currentTime);
  const [endS, setEndS] = useState(Math.min(currentTime + 10, videoDuration ?? currentTime + 10));
  const [eventType, setEventType] = useState<EventType>("observation");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (endS <= startS) {
      setError("End time must be after start time");
      return;
    }
    if (!title.trim()) {
      setError("Title is required");
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit({
        start_s: startS,
        end_s: endS,
        event_type: eventType,
        severity: severity || null,
        title: title.trim(),
        summary: summary.trim(),
      });
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 w-full max-w-md rounded-lg bg-white shadow-xl">
        <div className="border-b border-gray-200 px-4 py-3">
          <h2 className="text-lg font-medium text-gray-900">Add Event</h2>
        </div>

        <form onSubmit={handleSubmit} className="p-4">
          {error && (
            <div className="mb-4 rounded border border-red-200 bg-red-50 p-2 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Time range */}
          <div className="mb-4 grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Start Time
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={0}
                  max={videoDuration}
                  step={0.1}
                  value={startS}
                  onChange={(e) => setStartS(parseFloat(e.target.value) || 0)}
                  className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                />
                <span className="text-xs text-gray-500">{formatTime(startS)}</span>
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                End Time
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={0}
                  max={videoDuration}
                  step={0.1}
                  value={endS}
                  onChange={(e) => setEndS(parseFloat(e.target.value) || 0)}
                  className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                />
                <span className="text-xs text-gray-500">{formatTime(endS)}</span>
              </div>
            </div>
          </div>

          {/* Event type and severity */}
          <div className="mb-4 grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Event Type
              </label>
              <select
                value={eventType}
                onChange={(e) => setEventType(e.target.value as EventType)}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
              >
                {EVENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Severity (optional)
              </label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value as Severity | "")}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
              >
                <option value="">None</option>
                {SEVERITIES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Title */}
          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Brief event title"
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </div>

          {/* Summary */}
          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Summary
            </label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Describe the event..."
              rows={3}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "Creating..." : "Create Event"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
