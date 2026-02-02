import Link from "next/link";
import type { RunMetadata } from "@/types/api";
import { formatDate, formatDuration } from "@/lib/format";

interface RunCardProps {
  run: RunMetadata;
}

function StatusBadge({ status }: { status: RunMetadata["status"] }) {
  const colors = {
    pending: "bg-yellow-100 text-yellow-800",
    processing: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };

  return (
    <span className={`rounded-full px-2 py-1 text-xs font-medium ${colors[status]}`}>
      {status}
    </span>
  );
}

export function RunCard({ run }: RunCardProps) {
  return (
    <Link href={`/runs/${run.run_id}`}>
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md">
        <div className="mb-2 flex items-start justify-between">
          <h3 className="font-mono text-sm font-medium text-gray-900">
            {run.run_id.slice(0, 8)}...
          </h3>
          <StatusBadge status={run.status} />
        </div>

        {run.video_filename && (
          <p className="mb-2 truncate text-sm text-gray-600" title={run.video_filename}>
            {run.video_filename}
          </p>
        )}

        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>{formatDate(run.created_at)}</span>
          {run.duration_s && <span>{formatDuration(run.duration_s)}</span>}
        </div>
      </div>
    </Link>
  );
}
