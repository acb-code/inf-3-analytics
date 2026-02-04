"use client";

import { useMemo } from "react";
import type { SplitPoint } from "@/types/api";

interface SplitTimelineProps {
  durationS: number;
  splitPoints: SplitPoint[];
  onSplitClick?: (index: number) => void;
  selectedIndex?: number | null;
}

function formatTime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}

export function SplitTimeline({
  durationS,
  splitPoints,
  onSplitClick,
  selectedIndex,
}: SplitTimelineProps) {
  // Generate time markers
  const timeMarkers = useMemo(() => {
    const markers: { position: number; label: string }[] = [];
    // Show roughly 6-8 markers
    const interval = Math.ceil(durationS / 6 / 60) * 60; // Round to nearest minute
    for (let t = 0; t <= durationS; t += interval) {
      markers.push({
        position: (t / durationS) * 100,
        label: formatTime(t),
      });
    }
    // Always include end
    if (markers[markers.length - 1]?.position !== 100) {
      markers.push({
        position: 100,
        label: formatTime(durationS),
      });
    }
    return markers;
  }, [durationS]);

  const getTypeColor = (type: string): string => {
    switch (type) {
      case "silence":
        return "bg-green-500";
      case "scene":
        return "bg-purple-500";
      case "interval":
        return "bg-blue-500";
      case "user":
        return "bg-orange-500";
      default:
        return "bg-gray-500";
    }
  };

  return (
    <div className="w-full">
      {/* Timeline bar */}
      <div className="relative h-8 bg-gray-200 rounded-lg overflow-visible">
        {/* Split point markers */}
        {splitPoints.map((split, index) => {
          const position = (split.timestamp_s / durationS) * 100;
          const isSelected = selectedIndex === index;
          return (
            <button
              key={index}
              className={`absolute top-0 h-full w-1 transform -translate-x-1/2 cursor-pointer transition-all ${
                getTypeColor(split.type)
              } ${isSelected ? "w-2 ring-2 ring-offset-1 ring-blue-400" : "hover:w-2"}`}
              style={{ left: `${position}%` }}
              onClick={() => onSplitClick?.(index)}
              title={`${split.timestamp_ts} (${split.type}, ${Math.round(split.confidence * 100)}% confidence)`}
            >
              {/* Marker dot */}
              <div
                className={`absolute -top-1 left-1/2 transform -translate-x-1/2 w-3 h-3 rounded-full ${
                  getTypeColor(split.type)
                } border-2 border-white shadow`}
              />
            </button>
          );
        })}
      </div>

      {/* Time markers */}
      <div className="relative h-6 mt-1">
        {timeMarkers.map((marker, index) => (
          <div
            key={index}
            className="absolute transform -translate-x-1/2 text-xs text-gray-500"
            style={{ left: `${marker.position}%` }}
          >
            {marker.label}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex gap-4 mt-2 text-xs text-gray-600">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span>Silence</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-blue-500" />
          <span>Interval</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-orange-500" />
          <span>User</span>
        </div>
      </div>
    </div>
  );
}
