"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";

const ALLOWED_EXTENSIONS = [".mp4", ".mov", ".avi", ".mkv", ".webm"];
const MAX_SIZE_MB = 2048;
const LONG_VIDEO_THRESHOLD_MINUTES = 30;

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

export default function UploadPage() {
  const router = useRouter();
  const { lang, setLang, t } = useLanguage();
  const [file, setFile] = useState<File | null>(null);
  const [videoDuration, setVideoDuration] = useState<number | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [showDecomposePrompt, setShowDecomposePrompt] = useState(false);
  const [dismissedPrompt, setDismissedPrompt] = useState(false);

  // Check video duration when file changes
  useEffect(() => {
    if (!file) {
      setVideoDuration(null);
      setShowDecomposePrompt(false);
      return;
    }

    const video = document.createElement("video");
    video.preload = "metadata";

    video.onloadedmetadata = () => {
      URL.revokeObjectURL(video.src);
      const duration = video.duration;
      setVideoDuration(duration);

      if (duration > LONG_VIDEO_THRESHOLD_MINUTES * 60 && !dismissedPrompt) {
        setShowDecomposePrompt(true);
      }
    };

    video.onerror = () => {
      URL.revokeObjectURL(video.src);
      setVideoDuration(null);
    };

    video.src = URL.createObjectURL(file);
  }, [file, dismissedPrompt]);

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
      setDismissedPrompt(false);

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
      setDismissedPrompt(false);
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

  const handleUpload = useCallback(async () => {
    if (!file) return;

    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      const result = await api.uploadVideo(file, setProgress, lang);
      router.push(`/runs/${result.run_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setUploading(false);
    }
  }, [file, router, lang]);

  const handleRemove = useCallback(() => {
    setFile(null);
    setError(null);
    setProgress(0);
    setVideoDuration(null);
    setShowDecomposePrompt(false);
    setDismissedPrompt(false);
  }, []);

  const handleDismissPrompt = useCallback(() => {
    setShowDecomposePrompt(false);
    setDismissedPrompt(true);
  }, []);

  const isLongVideo = videoDuration !== null && videoDuration > LONG_VIDEO_THRESHOLD_MINUTES * 60;

  return (
    <div className="mx-auto max-w-2xl p-6">
      <header className="mb-6">
        <Link href="/runs" className="text-gray-600 hover:text-gray-900">
          {t("upload.back")}
        </Link>
        <h1 className="mt-4 text-2xl font-bold text-gray-900">{t("upload.title")}</h1>
        <p className="mt-2 text-gray-600">{t("upload.description")}</p>
      </header>

      {/* Decompose link */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex items-start gap-3">
          <svg
            className="h-5 w-5 text-blue-500 mt-0.5 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
          <div>
            <p className="text-sm text-gray-700">
              <strong>{t("upload.haveALongVideo")}</strong> {t("upload.decomposeSuggestion")}
            </p>
            <Link
              href="/decompose"
              className="inline-block mt-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              {t("upload.decomposeLink")}
            </Link>
          </div>
        </div>
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
                {videoDuration !== null && (
                  <span> · {formatDuration(videoDuration)}</span>
                )}
              </p>
            </div>
            {!uploading && (
              <button
                onClick={handleRemove}
                className="text-sm text-red-600 hover:text-red-800"
              >
                {t("upload.remove")}
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
                {t("upload.dragDrop")}{" "}
                <label className="cursor-pointer text-blue-600 hover:text-blue-800">
                  {t("upload.browse")}
                  <input
                    type="file"
                    className="hidden"
                    accept={ALLOWED_EXTENSIONS.join(",")}
                    onChange={handleFileSelect}
                  />
                </label>
              </p>
              <p className="mt-1 text-sm text-gray-500">
                Supported: {ALLOWED_EXTENSIONS.join(", ")} (max {MAX_SIZE_MB}MB)
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Long video decomposition prompt */}
      {showDecomposePrompt && file && (
        <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-start gap-3">
            <svg
              className="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <div className="flex-1">
              <p className="text-sm font-medium text-amber-800">
                {t("upload.longVideoTitle").replace("{duration}", formatDuration(videoDuration!))}
              </p>
              <p className="mt-1 text-sm text-amber-700">{t("upload.longVideoBody")}</p>
              <div className="mt-3 flex gap-3">
                <Link
                  href="/decompose"
                  className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-white bg-amber-600 rounded hover:bg-amber-700"
                >
                  {t("upload.decompose")}
                </Link>
                <button
                  onClick={handleDismissPrompt}
                  className="px-3 py-1.5 text-sm text-amber-700 hover:text-amber-900"
                >
                  {t("upload.continueAnyway")}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Language selector */}
      <div className="mt-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("upload.language")}
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setLang("en")}
            disabled={uploading}
            className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${
              lang === "en"
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
            } ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            English
          </button>
          <button
            type="button"
            onClick={() => setLang("fr")}
            disabled={uploading}
            className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${
              lang === "fr"
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
            } ${uploading ? "opacity-50 cursor-not-allowed" : ""}`}
          >
            Français
          </button>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          {lang === "fr" ? t("upload.languageHint.fr") : t("upload.languageHint")}
        </p>
      </div>

      {/* Error message */}
      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-red-700">
          {error}
        </div>
      )}

      {/* Progress bar */}
      {uploading && (
        <div className="mt-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">{t("upload.uploading")}</span>
            <span className="font-medium">{progress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Upload button */}
      <div className="mt-6">
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className={`w-full rounded-lg px-4 py-3 font-medium text-white transition-colors ${
            !file || uploading
              ? "cursor-not-allowed bg-gray-400"
              : "bg-blue-600 hover:bg-blue-700"
          }`}
        >
          {uploading ? t("upload.uploading") : t("upload.uploadButton")}
        </button>
        {isLongVideo && !showDecomposePrompt && (
          <p className="mt-2 text-center text-xs text-gray-500">
            {t("upload.longVideoNote").replace("{duration}", formatDuration(videoDuration!))}
          </p>
        )}
      </div>
    </div>
  );
}
