"use client";

import { useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { SplitTimeline } from "@/components/SplitTimeline";
import { SplitPointEditor } from "@/components/SplitPointEditor";
import { DecompositionProgress } from "@/components/DecompositionProgress";
import type {
  SplitPoint,
  SegmentPreview,
  SegmentResult,
  DecompositionPlanResponse,
} from "@/types/api";

const ALLOWED_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm"];
const MAX_SIZE_MB = 10240; // 10GB

type Step = "upload" | "analyze" | "review" | "execute" | "complete";

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}

export default function DecomposePage() {
  const router = useRouter();

  // Step state
  const [currentStep, setCurrentStep] = useState<Step>("upload");

  // Upload state
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Analysis state
  const [analyzing, setAnalyzing] = useState(false);
  const [plan, setPlan] = useState<DecompositionPlanResponse | null>(null);
  const [targetDuration, setTargetDuration] = useState(300); // 5 minutes

  // Edit state
  const [splitPoints, setSplitPoints] = useState<SplitPoint[]>([]);
  const [selectedSplitIndex, setSelectedSplitIndex] = useState<number | null>(null);

  // Execute state
  const [createChildRuns, setCreateChildRuns] = useState(true);
  const [jobId, setJobId] = useState<string | null>(null);

  // Complete state
  const [completedSegments, setCompletedSegments] = useState<SegmentResult[]>([]);
  const [childRunIds, setChildRunIds] = useState<string[]>([]);

  // Error state
  const [error, setError] = useState<string | null>(null);

  // Calculate segments from current split points
  const segments = useMemo((): SegmentPreview[] => {
    if (!plan) return [];

    const timestamps = [0, ...splitPoints.map((sp) => sp.timestamp_s), plan.duration_s];
    const bitrate = plan.file_size_mb / plan.duration_s;

    return timestamps.slice(0, -1).map((start, index) => {
      const end = timestamps[index + 1];
      const duration = end - start;
      return {
        index,
        start_s: start,
        end_s: end,
        duration_s: duration,
        start_ts: formatTimestamp(start),
        end_ts: formatTimestamp(end),
        estimated_size_mb: Math.round(duration * bitrate * 100) / 100,
      };
    });
  }, [plan, splitPoints]);

  function formatTimestamp(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${secs.toFixed(3).padStart(6, "0")}`;
  }

  // File validation
  const validateFile = useCallback((file: File): string | null => {
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File too large. Maximum size: ${MAX_SIZE_MB}MB`;
    }
    return null;
  }, []);

  // Drag handlers
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      setError(null);

      const droppedFile = e.dataTransfer.files?.[0];
      if (droppedFile) {
        const err = validateFile(droppedFile);
        if (err) {
          setError(err);
        } else {
          setFile(droppedFile);
        }
      }
    },
    [validateFile]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setError(null);
      const selectedFile = e.target.files?.[0];
      if (selectedFile) {
        const err = validateFile(selectedFile);
        if (err) {
          setError(err);
        } else {
          setFile(selectedFile);
        }
      }
    },
    [validateFile]
  );

  // Upload and analyze
  const handleUploadAndAnalyze = useCallback(async () => {
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);
    setError(null);

    try {
      // Upload file
      const uploadResult = await api.uploadVideo(file, setUploadProgress);
      const videoPath = uploadResult.video_path;

      setCurrentStep("analyze");
      setUploading(false);
      setAnalyzing(true);

      // Analyze for decomposition
      const analysisResult = await api.analyzeForDecomposition({
        video_path: videoPath,
        target_segment_duration_s: targetDuration,
      });

      setPlan(analysisResult);
      setSplitPoints(analysisResult.suggested_splits);
      setCurrentStep("review");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload/analysis failed");
      setCurrentStep("upload");
    } finally {
      setUploading(false);
      setAnalyzing(false);
    }
  }, [file, targetDuration]);

  // Split point editing
  const handleRemoveSplit = useCallback((index: number) => {
    setSplitPoints((prev) => prev.filter((_, i) => i !== index));
    setSelectedSplitIndex(null);
  }, []);

  const handleAddSplit = useCallback(
    (timestampS: number) => {
      if (!plan) return;

      const newSplit: SplitPoint = {
        timestamp_s: timestampS,
        timestamp_ts: formatTimestamp(timestampS),
        type: "user",
        keyframe_s: timestampS, // Will be snapped by backend
        confidence: 1.0,
      };

      setSplitPoints((prev) => {
        const updated = [...prev, newSplit];
        return updated.sort((a, b) => a.timestamp_s - b.timestamp_s);
      });
    },
    [plan]
  );

  const handleAdjustSplit = useCallback((index: number, newTimestampS: number) => {
    setSplitPoints((prev) => {
      const updated = [...prev];
      updated[index] = {
        ...updated[index],
        timestamp_s: newTimestampS,
        timestamp_ts: formatTimestamp(newTimestampS),
        type: "user",
        confidence: 1.0,
      };
      return updated.sort((a, b) => a.timestamp_s - b.timestamp_s);
    });
  }, []);

  // Execute decomposition
  const handleExecute = useCallback(async () => {
    if (!plan || splitPoints.length === 0) return;

    setError(null);
    setCurrentStep("execute");

    try {
      const result = await api.executeDecomposition({
        video_path: plan.video_path,
        split_timestamps: splitPoints.map((sp) => sp.timestamp_s),
        create_child_runs: createChildRuns,
      });

      setJobId(result.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start decomposition");
      setCurrentStep("review");
    }
  }, [plan, splitPoints, createChildRuns]);

  // Handle completion
  const handleComplete = useCallback(
    (segments: SegmentResult[], runIds: string[]) => {
      setCompletedSegments(segments);
      setChildRunIds(runIds);
      setCurrentStep("complete");
    },
    []
  );

  const handleExecutionError = useCallback((errorMsg: string) => {
    setError(errorMsg);
    setCurrentStep("review");
  }, []);

  // Render based on current step
  return (
    <div className="mx-auto max-w-4xl p-6">
      <header className="mb-6">
        <Link href="/runs" className="text-gray-600 hover:text-gray-900">
          &larr; Back to Runs
        </Link>
        <h1 className="mt-4 text-2xl font-bold text-gray-900">
          Video Decomposition
        </h1>
        <p className="text-gray-600">
          Split large videos into smaller segments for efficient processing
        </p>
      </header>

      {/* Step indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {["upload", "analyze", "review", "execute", "complete"].map(
            (step, index) => (
              <div key={step} className="flex items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    currentStep === step
                      ? "bg-blue-600 text-white"
                      : ["upload", "analyze", "review", "execute", "complete"].indexOf(
                          currentStep
                        ) > index
                      ? "bg-green-500 text-white"
                      : "bg-gray-200 text-gray-600"
                  }`}
                >
                  {index + 1}
                </div>
                {index < 4 && (
                  <div
                    className={`w-16 sm:w-24 h-1 mx-2 ${
                      ["upload", "analyze", "review", "execute", "complete"].indexOf(
                        currentStep
                      ) > index
                        ? "bg-green-500"
                        : "bg-gray-200"
                    }`}
                  />
                )}
              </div>
            )
          )}
        </div>
        <div className="flex justify-between mt-2 text-xs text-gray-500">
          <span>Upload</span>
          <span>Analyze</span>
          <span>Review</span>
          <span>Execute</span>
          <span>Complete</span>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {/* Step 1: Upload */}
      {currentStep === "upload" && (
        <div className="space-y-6">
          <h2 className="text-lg font-medium text-gray-900">
            Step 1: Select Video
          </h2>

          {/* Target duration setting */}
          <div className="flex items-center gap-4">
            <label className="text-sm text-gray-600">Target segment duration:</label>
            <select
              value={targetDuration}
              onChange={(e) => setTargetDuration(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value={180}>3 minutes</option>
              <option value={300}>5 minutes</option>
              <option value={600}>10 minutes</option>
              <option value={900}>15 minutes</option>
            </select>
          </div>

          {/* Dropzone */}
          <div
            className={`relative rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
              dragActive
                ? "border-blue-500 bg-blue-50"
                : file
                  ? "border-green-500 bg-green-50"
                  : "border-gray-300 hover:border-gray-400"
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            {file ? (
              <div className="space-y-4">
                <svg
                  className="mx-auto h-12 w-12 text-green-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div>
                  <p className="font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / (1024 * 1024)).toFixed(1)} MB
                  </p>
                </div>
                {!uploading && (
                  <button
                    onClick={() => setFile(null)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Remove
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
                <div>
                  <p className="text-gray-700">
                    Drag and drop a video file here, or{" "}
                    <label className="cursor-pointer text-blue-600 hover:text-blue-800">
                      browse
                      <input
                        type="file"
                        className="hidden"
                        accept={ALLOWED_EXTENSIONS.join(",")}
                        onChange={handleFileSelect}
                      />
                    </label>
                  </p>
                  <p className="mt-1 text-sm text-gray-500">
                    Supported: {ALLOWED_EXTENSIONS.join(", ")} (max {MAX_SIZE_MB / 1024}GB)
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Upload progress */}
          {uploading && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Uploading...</span>
                <span className="font-medium">{uploadProgress}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-gray-200">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Upload button */}
          <button
            onClick={handleUploadAndAnalyze}
            disabled={!file || uploading}
            className={`w-full rounded-lg px-4 py-3 font-medium text-white transition-colors ${
              !file || uploading
                ? "cursor-not-allowed bg-gray-400"
                : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            {uploading ? "Uploading..." : "Upload & Analyze"}
          </button>
        </div>
      )}

      {/* Step 2: Analyzing */}
      {currentStep === "analyze" && (
        <div className="flex flex-col items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4" />
          <p className="text-gray-600">Analyzing video for optimal split points...</p>
          <p className="text-sm text-gray-500 mt-2">
            This may take a few seconds for long videos
          </p>
        </div>
      )}

      {/* Step 3: Review */}
      {currentStep === "review" && plan && (
        <div className="space-y-6">
          <h2 className="text-lg font-medium text-gray-900">
            Step 2: Review Split Points
          </h2>

          {/* Video info */}
          <div className="flex flex-wrap gap-4 text-sm">
            <div className="px-3 py-2 bg-gray-100 rounded-lg">
              <span className="text-gray-500">Duration:</span>{" "}
              <span className="font-medium">{formatDuration(plan.duration_s)}</span>
            </div>
            <div className="px-3 py-2 bg-gray-100 rounded-lg">
              <span className="text-gray-500">Size:</span>{" "}
              <span className="font-medium">{plan.file_size_mb.toFixed(1)} MB</span>
            </div>
            <div className="px-3 py-2 bg-gray-100 rounded-lg">
              <span className="text-gray-500">Segments:</span>{" "}
              <span className="font-medium">{segments.length}</span>
            </div>
          </div>

          {/* Timeline */}
          <div className="p-4 bg-white rounded-lg border border-gray-200">
            <h3 className="text-sm font-medium text-gray-700 mb-4">Timeline</h3>
            <SplitTimeline
              durationS={plan.duration_s}
              splitPoints={splitPoints}
              onSplitClick={setSelectedSplitIndex}
              selectedIndex={selectedSplitIndex}
            />
          </div>

          {/* Split point editor */}
          <div className="p-4 bg-white rounded-lg border border-gray-200">
            <h3 className="text-sm font-medium text-gray-700 mb-4">
              Split Points
            </h3>
            <SplitPointEditor
              splitPoints={splitPoints}
              segments={segments}
              onRemoveSplit={handleRemoveSplit}
              onAddSplit={handleAddSplit}
              onAdjustSplit={handleAdjustSplit}
              durationS={plan.duration_s}
              selectedIndex={selectedSplitIndex}
              onSelectSplit={setSelectedSplitIndex}
            />
          </div>

          {/* Options */}
          <div className="p-4 bg-white rounded-lg border border-gray-200">
            <h3 className="text-sm font-medium text-gray-700 mb-4">Options</h3>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={createChildRuns}
                onChange={(e) => setCreateChildRuns(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">
                Create separate runs for each segment (recommended)
              </span>
            </label>
          </div>

          {/* Summary */}
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-sm text-blue-800">
              <strong>Estimated:</strong> {segments.length} segments, avg{" "}
              {formatDuration(plan.duration_s / segments.length)} each,{" "}
              ~{plan.file_size_mb.toFixed(0)} MB total
            </p>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <button
              onClick={() => {
                setCurrentStep("upload");
                setFile(null);
                setPlan(null);
                setSplitPoints([]);
              }}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button
              onClick={handleExecute}
              disabled={splitPoints.length === 0}
              className={`px-6 py-2 rounded-lg font-medium text-white ${
                splitPoints.length === 0
                  ? "bg-gray-400 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              Start Decomposition
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Executing */}
      {currentStep === "execute" && jobId && (
        <div className="space-y-6">
          <h2 className="text-lg font-medium text-gray-900">
            Step 3: Decomposing Video
          </h2>
          <DecompositionProgress
            jobId={jobId}
            onComplete={handleComplete}
            onError={handleExecutionError}
          />
        </div>
      )}

      {/* Step 5: Complete */}
      {currentStep === "complete" && (
        <div className="space-y-6">
          <div className="flex items-center gap-2 text-green-600">
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <h2 className="text-lg font-medium">Decomposition Complete</h2>
          </div>

          <p className="text-gray-600">
            Created {completedSegments.length} segments
            {childRunIds.length > 0 && ` with ${childRunIds.length} child runs`}
          </p>

          {/* Segments table */}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    #
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Run ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Duration
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Size
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {completedSegments.map((segment) => (
                  <tr key={segment.index} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {segment.index + 1}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      {segment.child_run_id ? (
                        <Link
                          href={`/runs/${segment.child_run_id}`}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          {segment.child_run_id}
                        </Link>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {formatDuration(segment.duration_s)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {segment.file_size_mb.toFixed(1)} MB
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      {segment.child_run_id && (
                        <Link
                          href={`/runs/${segment.child_run_id}`}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          View
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <Link
              href="/runs"
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Go to Runs List
            </Link>
            {childRunIds.length > 0 && (
              <Link
                href={`/runs/${childRunIds[0]}`}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                View First Segment
              </Link>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
