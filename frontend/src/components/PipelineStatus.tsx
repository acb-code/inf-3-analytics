"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { PipelineStatusResponse, PipelineStep, PipelineStepInfo, StepStatus } from "@/types/api";

interface PipelineStatusProps {
  runId: string;
  onComplete?: () => void;
  onStatusUpdate?: (status: PipelineStatusResponse) => void;
  pollInterval?: number;
}

const STEP_LABELS: Record<string, string> = {
  transcribe: "Transcribe Audio",
  extract_events: "Extract Events",
  extract_frames: "Extract Frames",
  frame_analytics: "Analyze Frames",
};

function StatusIcon({ status }: { status: StepStatus }) {
  switch (status) {
    case "completed":
      return (
        <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      );
    case "running":
      return (
        <svg className="h-5 w-5 animate-spin text-blue-500" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      );
    case "failed":
      return (
        <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      );
    case "skipped":
      return (
        <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
        </svg>
      );
    case "pending":
    default:
      return (
        <div className="h-5 w-5 rounded-full border-2 border-gray-300" />
      );
  }
}

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      className={`h-4 w-4 text-gray-500 transition-transform ${expanded ? "rotate-90" : ""}`}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  );
}

function StepRow({
  step,
  expanded,
  onToggle,
  onCancel,
  canceling,
}: {
  step: PipelineStepInfo;
  expanded: boolean;
  onToggle: () => void;
  onCancel?: () => void;
  canceling?: boolean;
}) {
  const label = STEP_LABELS[step.step] || step.step;
  const hasOutput = step.output || step.error_message;
  const isClickable = hasOutput || step.status === "running";
  const hasProgress =
    step.progress_total !== null &&
    step.progress_total !== undefined &&
    step.progress_total > 0 &&
    step.progress_current !== null &&
    step.progress_current !== undefined;
  const progressPercent = hasProgress
    ? Math.min(100, Math.round((step.progress_current! / step.progress_total!) * 100))
    : 0;

  return (
    <div>
      <div
        className={`flex items-center gap-3 py-3 ${isClickable ? "cursor-pointer hover:bg-gray-50" : ""}`}
        onClick={isClickable ? onToggle : undefined}
      >
        <StatusIcon status={step.status} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900">{label}</span>
            {step.status === "running" && (
              <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">Running...</span>
            )}
          </div>
          {hasProgress && (
            <div className="mt-1 text-xs text-gray-600">
              {step.progress_message || "Progress"}: {step.progress_current} / {step.progress_total}{" "}
              {step.progress_unit || "items"}
            </div>
          )}
          {hasProgress && (
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full bg-blue-500 transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          )}
          {step.status === "completed" && step.completed_at && (
            <div className="text-xs text-gray-500">
              Completed {new Date(step.completed_at).toLocaleTimeString()}
            </div>
          )}
          {step.status === "failed" && (
            <div className="text-xs text-red-600">Failed - click to see details</div>
          )}
        </div>
        {step.status === "running" && onCancel && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCancel();
            }}
            className="rounded border border-red-200 bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
            disabled={canceling}
          >
            {canceling ? "Cancelling..." : "Cancel"}
          </button>
        )}
        {hasOutput && <ChevronIcon expanded={expanded} />}
      </div>

      {/* Expandable output section */}
      {expanded && hasOutput && (
        <div className="mb-3 ml-8 overflow-hidden rounded border border-gray-700 bg-gray-900">
          <div className="flex items-center justify-between border-b border-gray-700 bg-gray-800 px-3 py-1.5">
            <span className="text-xs font-medium text-gray-300">Output</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                navigator.clipboard.writeText(step.output || step.error_message || "");
              }}
              className="text-xs text-gray-400 hover:text-white"
            >
              Copy
            </button>
          </div>
          <pre className="max-h-64 overflow-auto p-3 text-xs text-gray-100 font-mono whitespace-pre-wrap">
            {step.output || step.error_message}
          </pre>
        </div>
      )}
    </div>
  );
}

export function PipelineStatus({ runId, onComplete, onStatusUpdate, pollInterval = 2000 }: PipelineStatusProps) {
  const [status, setStatus] = useState<PipelineStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [cancelingStep, setCancelingStep] = useState<PipelineStep | null>(null);
  const [polling, setPolling] = useState(true);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const toggleStep = useCallback((stepName: string) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepName)) {
        next.delete(stepName);
      } else {
        next.add(stepName);
      }
      return next;
    });
  }, []);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await api.getPipelineStatus(runId);
      setStatus(data);
      setError(null);
      setActionError(null);

      // Notify parent of status update
      onStatusUpdate?.(data);

      // Auto-expand running or failed steps
      const stepsToExpand = data.steps
        .filter((s) => s.status === "running" || s.status === "failed")
        .map((s) => s.step);
      if (stepsToExpand.length > 0) {
        setExpandedSteps((prev) => {
          const next = new Set(prev);
          stepsToExpand.forEach((s) => next.add(s));
          return next;
        });
      }

      // Stop polling if pipeline is done
      const isDone =
        data.run_status === "completed" ||
        data.run_status === "failed" ||
        data.steps.every((s) => s.status === "completed" || s.status === "failed" || s.status === "skipped");

      if (isDone) {
        setPolling(false);
        onComplete?.();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch status");
    }
  }, [runId, onComplete, onStatusUpdate]);

  const handleCancelStep = useCallback(
    async (step: PipelineStep) => {
      setActionError(null);
      setCancelingStep(step);
      try {
        await api.cancelPipelineStep(runId, step);
        await fetchStatus();
      } catch (err) {
        setActionError(err instanceof Error ? err.message : "Failed to cancel step");
      } finally {
        setCancelingStep(null);
      }
    },
    [runId, fetchStatus]
  );

  useEffect(() => {
    fetchStatus();

    if (polling) {
      const interval = setInterval(fetchStatus, pollInterval);
      return () => clearInterval(interval);
    }
  }, [fetchStatus, polling, pollInterval]);

  if (error && !status) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="animate-pulse space-y-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center gap-3">
            <div className="h-5 w-5 rounded-full bg-gray-200" />
            <div className="h-4 flex-1 rounded bg-gray-200" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Progress</span>
          <span className="font-medium">{status.progress_percent}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-gray-200">
          <div
            className={`h-full transition-all duration-300 ${
              status.run_status === "failed"
                ? "bg-red-500"
                : status.run_status === "completed"
                  ? "bg-green-500"
                  : "bg-blue-500"
            }`}
            style={{ width: `${status.progress_percent}%` }}
          />
        </div>
      </div>

      {actionError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-2 text-sm text-red-700">
          {actionError}
        </div>
      )}

      {/* Steps list */}
      <div className="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
        {status.steps.map((step) => (
          <div key={step.step} className="px-4">
            <StepRow
              step={step}
              expanded={expandedSteps.has(step.step)}
              onToggle={() => toggleStep(step.step)}
              onCancel={
                step.status === "running"
                  ? () => handleCancelStep(step.step)
                  : undefined
              }
              canceling={cancelingStep === step.step}
            />
          </div>
        ))}
      </div>

      {/* Status message */}
      {status.run_status === "completed" && (
        <div className="rounded-lg bg-green-50 p-3 text-center text-green-700">
          Pipeline completed successfully
        </div>
      )}
      {status.run_status === "failed" && (
        <div className="rounded-lg bg-red-50 p-3 text-center text-red-700">
          Pipeline failed. Expand failed steps to see error details.
        </div>
      )}
    </div>
  );
}
