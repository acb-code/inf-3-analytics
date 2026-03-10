 "use client";

import { useRouter } from "next/navigation";
import type { RunMetadata } from "@/types/api";
import { formatDate } from "@/lib/format";
import { useLanguage } from "@/lib/i18n";
import { LoadingIndicator } from "@/components/LoadingSpinner";

interface RunCardProps {
  run: RunMetadata;
  onDelete?: (run: RunMetadata, force?: boolean) => void;
  deleting?: boolean;
}

function StatusBadge({ status }: { status: RunMetadata["status"] }) {
  const { t } = useLanguage();
  const colors = {
    created: "bg-gray-100 text-gray-800",
    running: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };

  return (
    <span className={`rounded-full px-2 py-1 text-xs font-medium ${colors[status]}`}>
      {t(`status.${status}` as Parameters<typeof t>[0])}
    </span>
  );
}

export function RunCard({ run, onDelete, deleting = false }: RunCardProps) {
  const router = useRouter();
  const { t } = useLanguage();

  const handleNavigate = () => {
    router.push(`/runs/${run.run_id}`);
  };

  return (
    <div
      className="relative cursor-pointer rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
      role="link"
      tabIndex={0}
      onClick={handleNavigate}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          handleNavigate();
        }
      }}
      aria-label={`View run ${run.run_id}`}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <h3 className="min-w-0 flex-1 break-all font-mono text-sm font-medium text-gray-900">
          {run.run_id}
        </h3>
        <div className="flex items-center gap-2">
          <StatusBadge status={run.status} />
          {run.status === "running" && <LoadingIndicator className="text-blue-600" />}
          {onDelete && (
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onDelete(run, run.status === "running");
              }}
              className="rounded border border-red-200 bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-50"
              disabled={deleting}
            >
              {deleting ? t("common.deleting") : t("common.delete")}
            </button>
          )}
        </div>
      </div>

      <p className="mb-2 break-words text-sm text-gray-600" title={run.video_basename}>
        {run.video_basename}
      </p>

      <div className="text-xs text-gray-500">
        <span>{formatDate(run.created_at)}</span>
      </div>
    </div>
  );
}
