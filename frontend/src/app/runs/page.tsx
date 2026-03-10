"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { RunMetadata } from "@/types/api";
import { RunCard } from "@/components/RunCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { useLanguage } from "@/lib/i18n";

export default function RunsPage() {
  const { lang, setLang, t } = useLanguage();
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
          <p className="font-medium">{t("home.errorLoading")}</p>
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
      {/* Branded header */}
      <header className="mb-8">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight text-gray-900">
                {t("home.appName")}
              </h1>
              {/* FR/EN toggle */}
              <div className="inline-flex rounded border border-gray-300 text-sm">
                <button
                  onClick={() => setLang("en")}
                  className={`px-3 py-1 ${
                    lang === "en"
                      ? "bg-blue-600 text-white"
                      : "bg-white text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  EN
                </button>
                <button
                  onClick={() => setLang("fr")}
                  className={`px-3 py-1 ${
                    lang === "fr"
                      ? "bg-blue-600 text-white"
                      : "bg-white text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  FR
                </button>
              </div>
            </div>
            <p className="mt-1 text-base font-medium text-blue-700">{t("home.tagline")}</p>
            <p className="mt-3 max-w-2xl text-sm text-gray-600">{t("home.description")}</p>
            <p className="mt-2 text-xs text-gray-400">{t("home.capabilities")}</p>
          </div>
          <Link
            href="/upload"
            className="shrink-0 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
          >
            {t("home.uploadVideo")}
          </Link>
        </div>
      </header>

      {/* Divider */}
      <div className="mb-6 border-t border-gray-200" />

      {/* Runs subtitle */}
      <p className="mb-4 text-sm text-gray-500">{t("home.selectRun")}</p>

      {actionError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {actionError}
        </div>
      )}

      {runs.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-gray-500">
          {t("home.noRuns")}
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
