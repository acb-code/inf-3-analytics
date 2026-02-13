"use client";

import type { Detection } from "@/types/api";

const TYPE_COLORS: Record<string, string> = {
  construction_equipment: "bg-blue-500",
  person: "bg-green-500",
  hardhat: "bg-yellow-500",
  crack: "bg-red-500",
  corrosion: "bg-red-500",
  safety_risk: "bg-red-500",
  leak: "bg-orange-500",
};

function getDotColor(type: string): string {
  return TYPE_COLORS[type] || "bg-gray-500";
}

interface DetectionToggleListProps {
  detections: Detection[];
  visibleIndices: Set<number>;
  onToggle: (index: number) => void;
  onShowAll: () => void;
  onHideAll: () => void;
}

export function DetectionToggleList({
  detections,
  visibleIndices,
  onToggle,
  onShowAll,
  onHideAll,
}: DetectionToggleListProps) {
  if (detections.length === 0) return null;

  // Group by type
  const groups: Record<string, { det: Detection; idx: number }[]> = {};
  detections.forEach((det, idx) => {
    const group = groups[det.type] || [];
    group.push({ det, idx });
    groups[det.type] = group;
  });

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <h5 className="text-xs font-medium uppercase text-gray-400">
          Detections ({detections.length})
        </h5>
        <div className="ml-auto flex gap-1">
          <button
            onClick={onShowAll}
            className="rounded bg-gray-700 px-1.5 py-0.5 text-[10px] text-gray-300 hover:bg-gray-600"
          >
            All
          </button>
          <button
            onClick={onHideAll}
            className="rounded bg-gray-700 px-1.5 py-0.5 text-[10px] text-gray-300 hover:bg-gray-600"
          >
            None
          </button>
        </div>
      </div>
      <div className="space-y-3">
        {Object.entries(groups).map(([type, items]) => (
          <div key={type}>
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500">
              {type.replace(/_/g, " ")}
            </p>
            <div className="space-y-1">
              {items.map(({ det, idx }) => (
                <label
                  key={idx}
                  className="flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 hover:bg-gray-700/50"
                >
                  <input
                    type="checkbox"
                    checked={visibleIndices.has(idx)}
                    onChange={() => onToggle(idx)}
                    className="h-3 w-3 rounded border-gray-600"
                  />
                  <span
                    className={`h-2 w-2 flex-shrink-0 rounded-full ${getDotColor(det.type)}`}
                  />
                  <span className="flex-1 truncate text-xs text-gray-200">
                    {det.label}
                  </span>
                  <span className="text-[10px] tabular-nums text-gray-500">
                    {Math.round(det.confidence * 100)}%
                  </span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
