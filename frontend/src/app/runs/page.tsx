"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { RunMetadata } from "@/types/api";
import { RunCard } from "@/components/RunCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";

export default function RunsPage() {
  const [runs, setRuns] = useState<RunMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deletingRunId, setDeletingRunId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    api
      .listRuns({ signal: controller.signal })
      .then((data) => {
        setRuns(data.runs);
        setLoading(false);
      })
      .catch((err) => {
        if (err?.name === "AbortError") return;
        setError(err.message);
        setLoading(false);
      });
    return () => controller.abort();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <p className="font-medium">Error loading runs</p>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  const handleDeleteRun = async (run: RunMetadata) => {
    setActionError(null);
    const confirmed = window.confirm(
      `Delete run ${run.run_id}? This only removes it from the registry.`
    );
    if (!confirmed) return;

    setDeletingRunId(run.run_id);
    try {
      await api.deleteRun(run.run_id);
      setRuns((prev) => prev.filter((item) => item.run_id !== run.run_id));
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to delete run");
    } finally {
      setDeletingRunId(null);
    }
  };

  return (
    <div className="mx-auto max-w-6xl p-6">
      <header className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inspection Runs</h1>
          <p className="text-gray-600">Select a run to view video and events</p>
        </div>
        <Link
          href="/upload"
          className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
        >
          Upload Video
        </Link>
      </header>

      {actionError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {actionError}
        </div>
      )}

      {runs.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-gray-500">
          No runs found. Process a video to get started.
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {runs.map((run) => (
            <RunCard
              key={run.run_id}
              run={run}
              onDelete={handleDeleteRun}
              deleting={deletingRunId === run.run_id}
            />
          ))}
        </div>
      )}
    </div>
  );
}
