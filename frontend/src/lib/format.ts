import type { Severity, EventType } from "@/types/api";

// Format seconds to MM:SS or HH:MM:SS
export function formatTime(seconds: number): string {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

// Format duration for display
export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins === 0) return `${secs}s`;
  if (secs === 0) return `${mins}m`;
  return `${mins}m ${secs}s`;
}

// Severity badge colors
export function getSeverityColor(severity: Severity): string {
  switch (severity) {
    case "high":
      return "bg-red-100 text-red-800 border-red-200";
    case "medium":
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    case "low":
      return "bg-green-100 text-green-800 border-green-200";
    default:
      return "bg-gray-100 text-gray-800 border-gray-200";
  }
}

// Event type badge colors
export function getEventTypeColor(eventType: EventType): string {
  switch (eventType) {
    case "structural_anomaly":
      return "bg-red-50 text-red-700 border-red-200";
    case "safety_risk":
      return "bg-rose-50 text-rose-700 border-rose-200";
    case "maintenance_note":
      return "bg-amber-50 text-amber-700 border-amber-200";
    case "measurement":
      return "bg-indigo-50 text-indigo-700 border-indigo-200";
    case "location_reference":
      return "bg-cyan-50 text-cyan-700 border-cyan-200";
    case "uncertainty":
      return "bg-orange-50 text-orange-700 border-orange-200";
    case "observation":
      return "bg-blue-50 text-blue-700 border-blue-200";
    default:
      return "bg-gray-50 text-gray-700 border-gray-200";
  }
}

// Format event type for display
export function formatEventType(eventType: EventType): string {
  return eventType.replace(/_/g, " ");
}

// Format date for display
export function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
