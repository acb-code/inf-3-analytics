"use client";

import type { Detection } from "@/types/api";

const DETECTION_COLORS: Record<string, string> = {
  construction_equipment: "#3b82f6", // blue
  person: "#22c55e", // green
  hardhat: "#eab308", // yellow
  crack: "#ef4444", // red
  corrosion: "#ef4444",
  safety_risk: "#ef4444",
  leak: "#f97316", // orange
};

function getDetectionColor(type: string): string {
  return DETECTION_COLORS[type] || "#9ca3af"; // gray fallback
}

interface BoundingBoxOverlayProps {
  detections: Detection[];
  visibleIndices: Set<number>;
}

export function BoundingBoxOverlay({
  detections,
  visibleIndices,
}: BoundingBoxOverlayProps) {
  return (
    <>
      {detections.map((det, idx) => {
        if (!visibleIndices.has(idx) || !det.bbox) return null;
        const color = getDetectionColor(det.type);
        return (
          <div
            key={idx}
            className="pointer-events-none absolute"
            style={{
              left: `${det.bbox.x * 100}%`,
              top: `${det.bbox.y * 100}%`,
              width: `${det.bbox.w * 100}%`,
              height: `${det.bbox.h * 100}%`,
              border: `2px solid ${color}`,
            }}
          >
            <span
              className="absolute -top-5 left-0 whitespace-nowrap rounded px-1 text-[10px] font-medium leading-tight text-white"
              style={{ backgroundColor: color }}
            >
              {det.label} {Math.round(det.confidence * 100)}%
            </span>
          </div>
        );
      })}
    </>
  );
}
