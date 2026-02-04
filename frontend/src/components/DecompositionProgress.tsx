"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { DecompositionStatusResponse, SegmentResult } from "@/types/api";

interface DecompositionProgressProps {
  jobId: string;
  onComplete: (segments: SegmentResult[], childRunIds: string[]) => void;
  onError: (error: string) => void;
}

export function DecompositionProgress({
  jobId,
  onComplete,
  onError,
}: DecompositionProgressProps) {
  const [status, setStatus] = useState<DecompositionStatusResponse | null>(null);

  useEffect(() => {
    const cleanup = api.streamDecompositionStatus(jobId, {
      onStatus: (newStatus) => {
        setStatus(newStatus);
      },
      onDone: (data) => {
        if (data.status === "completed" && status) {
          onComplete(status.segments_created, status.child_run_ids);
        } else if (data.status === "failed" && status?.error_message) {
          onError(status.error_message);
        }
      },
      onError: (error) => {
        onError(error.message);
      },
    });

    return cleanup;
  }, [jobId, onComplete, onError, status]);

  // Also check status on mount in case SSE missed something
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const currentStatus = await api.getDecompositionStatus(jobId);
        setStatus(currentStatus);
        if (currentStatus.status === "completed") {
          onComplete(currentStatus.segments_created, currentStatus.child_run_ids);
        } else if (currentStatus.status === "failed" && currentStatus.error_message) {
          onError(currentStatus.error_message);
        }
      } catch {
        // SSE will handle it
      }
    };
    checkStatus();
  }, [jobId, onComplete, onError]);

  if (!status) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const progressPercent =
    status.progress_total > 0
      ? Math.round((status.progress_current / status.progress_total) * 100)
      : 0;

  const getStatusColor = (): string => {
    switch (status.status) {
      case "completed":
        return "text-green-600";
      case "failed":
        return "text-red-600";
      default:
        return "text-blue-600";
    }
  };

  const getStatusLabel = (): string => {
    switch (status.status) {
      case "analyzing":
        return "Analyzing video...";
      case "splitting":
        return "Splitting video...";
      case "creating_runs":
        return "Creating child runs...";
      case "completed":
        return "Completed";
      case "failed":
        return "Failed";
      default:
        return status.status;
    }
  };

  return (
    <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
      {/* Status header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {status.status !== "completed" && status.status !== "failed" && (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" />
          )}
          <span className={`font-medium ${getStatusColor()}`}>
            {getStatusLabel()}
          </span>
        </div>
        <span className="text-sm text-gray-500">
          {status.progress_current} / {status.progress_total}
        </span>
      </div>

      {/* Progress bar */}
      {status.status !== "completed" && status.status !== "failed" && (
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      )}

      {/* Progress message */}
      {status.progress_message && (
        <p className="text-sm text-gray-600">{status.progress_message}</p>
      )}

      {/* Error message */}
      {status.error_message && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {status.error_message}
        </div>
      )}

      {/* Segments created */}
      {status.segments_created.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Segments Created ({status.segments_created.length})
          </h4>
          <div className="max-h-48 overflow-y-auto space-y-1">
            {status.segments_created.map((segment) => (
              <div
                key={segment.index}
                className="flex items-center justify-between p-2 bg-white rounded border border-gray-200 text-sm"
              >
                <span className="font-medium">
                  Segment {segment.index + 1}
                </span>
                <span className="text-gray-500">
                  {segment.file_size_mb.toFixed(1)} MB
                  {segment.child_run_id && (
                    <span className="ml-2 text-blue-600">
                      → {segment.child_run_id}
                    </span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
