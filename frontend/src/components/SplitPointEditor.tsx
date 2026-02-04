"use client";

import { useState } from "react";
import type { SplitPoint, SegmentPreview } from "@/types/api";

interface SplitPointEditorProps {
  splitPoints: SplitPoint[];
  segments: SegmentPreview[];
  onRemoveSplit: (index: number) => void;
  onAddSplit: (timestampS: number) => void;
  onAdjustSplit: (index: number, newTimestampS: number) => void;
  durationS: number;
  selectedIndex: number | null;
  onSelectSplit: (index: number | null) => void;
}

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}

export function SplitPointEditor({
  splitPoints,
  segments,
  onRemoveSplit,
  onAddSplit,
  onAdjustSplit,
  durationS,
  selectedIndex,
  onSelectSplit,
}: SplitPointEditorProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTimestamp, setNewTimestamp] = useState("");
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editTimestamp, setEditTimestamp] = useState("");

  const handleAddSplit = () => {
    // Parse timestamp (supports "MM:SS" or "HH:MM:SS" or seconds)
    let seconds = 0;
    if (newTimestamp.includes(":")) {
      const parts = newTimestamp.split(":").map(Number);
      if (parts.length === 2) {
        seconds = parts[0] * 60 + parts[1];
      } else if (parts.length === 3) {
        seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
      }
    } else {
      seconds = parseFloat(newTimestamp);
    }

    if (seconds > 0 && seconds < durationS) {
      onAddSplit(seconds);
      setNewTimestamp("");
      setShowAddModal(false);
    }
  };

  const handleStartEdit = (index: number, currentTimestamp: string) => {
    setEditingIndex(index);
    // Convert "HH:MM:SS.mmm" to "MM:SS" for easier editing
    const parts = currentTimestamp.split(":");
    if (parts.length === 3) {
      setEditTimestamp(`${parseInt(parts[0]) * 60 + parseInt(parts[1])}:${parts[2].split(".")[0]}`);
    } else {
      setEditTimestamp(currentTimestamp);
    }
  };

  const handleSaveEdit = (index: number) => {
    let seconds = 0;
    if (editTimestamp.includes(":")) {
      const parts = editTimestamp.split(":").map(Number);
      if (parts.length === 2) {
        seconds = parts[0] * 60 + parts[1];
      } else if (parts.length === 3) {
        seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
      }
    } else {
      seconds = parseFloat(editTimestamp);
    }

    if (seconds > 0 && seconds < durationS) {
      onAdjustSplit(index, seconds);
    }
    setEditingIndex(null);
    setEditTimestamp("");
  };

  const getTypeLabel = (type: string): string => {
    switch (type) {
      case "silence":
        return "Silence";
      case "scene":
        return "Scene";
      case "interval":
        return "Interval";
      case "user":
        return "User";
      default:
        return type;
    }
  };

  const getTypeBadgeColor = (type: string): string => {
    switch (type) {
      case "silence":
        return "bg-green-100 text-green-800";
      case "scene":
        return "bg-purple-100 text-purple-800";
      case "interval":
        return "bg-blue-100 text-blue-800";
      case "user":
        return "bg-orange-100 text-orange-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="space-y-4">
      {/* Split Points Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                #
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Time
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Confidence
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {splitPoints.map((split, index) => (
              <tr
                key={index}
                className={`${
                  selectedIndex === index ? "bg-blue-50" : "hover:bg-gray-50"
                } cursor-pointer`}
                onClick={() => onSelectSplit(selectedIndex === index ? null : index)}
              >
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                  {index + 1}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm">
                  {editingIndex === index ? (
                    <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="text"
                        value={editTimestamp}
                        onChange={(e) => setEditTimestamp(e.target.value)}
                        className="w-24 px-2 py-1 border border-gray-300 rounded text-sm"
                        placeholder="MM:SS"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveEdit(index);
                          if (e.key === "Escape") setEditingIndex(null);
                        }}
                      />
                      <button
                        onClick={() => handleSaveEdit(index)}
                        className="text-green-600 hover:text-green-800"
                      >
                        ✓
                      </button>
                      <button
                        onClick={() => setEditingIndex(null)}
                        className="text-gray-600 hover:text-gray-800"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <span className="font-mono">{split.timestamp_ts}</span>
                  )}
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span
                    className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getTypeBadgeColor(
                      split.type
                    )}`}
                  >
                    {getTypeLabel(split.type)}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                  {Math.round(split.confidence * 100)}%
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleStartEdit(index, split.timestamp_ts)}
                      className="text-blue-600 hover:text-blue-800"
                      title="Adjust"
                    >
                      Adjust
                    </button>
                    <button
                      onClick={() => onRemoveSplit(index)}
                      className="text-red-600 hover:text-red-800"
                      title="Remove"
                    >
                      Remove
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add Split Button */}
      <div className="flex justify-start">
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 border border-blue-300 rounded-lg hover:bg-blue-50"
        >
          <span>+</span> Add Split Point
        </button>
      </div>

      {/* Segments Preview */}
      <div className="mt-6">
        <h4 className="text-sm font-medium text-gray-700 mb-2">
          Resulting Segments ({segments.length})
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
          {segments.map((segment) => (
            <div
              key={segment.index}
              className="p-2 bg-gray-50 rounded border border-gray-200 text-sm"
            >
              <div className="font-medium text-gray-900">
                Segment {segment.index + 1}
              </div>
              <div className="text-gray-600 text-xs">
                {formatDuration(segment.duration_s)} · ~{segment.estimated_size_mb.toFixed(1)}MB
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Add Split Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-80 shadow-xl">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Add Split Point
            </h3>
            <input
              type="text"
              value={newTimestamp}
              onChange={(e) => setNewTimestamp(e.target.value)}
              placeholder="Enter time (MM:SS or seconds)"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") handleAddSplit();
                if (e.key === "Escape") setShowAddModal(false);
              }}
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleAddSplit}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
