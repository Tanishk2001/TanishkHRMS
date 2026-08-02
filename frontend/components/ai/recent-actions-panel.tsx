"use client";

import { useEffect, useState } from "react";
import { History, RefreshCw } from "lucide-react";
import { getRecentAiActions, AIAuditLogRow } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  SUCCESS: "bg-good/10 text-good border-good/25",
  DENIED: "bg-bad/10 text-bad border-bad/25",
  ERROR: "bg-bad/10 text-bad border-bad/25",
  NO_ANSWER: "bg-accent/10 text-accent border-accent/25",
  NEEDS_CONFIRMATION: "bg-accent/10 text-accent border-accent/25",
};

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function RecentActionsPanel() {
  const [logs, setLogs] = useState<AIAuditLogRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    getRecentAiActions(10)
      .then((res) => setLogs(res.data?.logs ?? []))
      .catch((e) => setError(e.message));
  }

  useEffect(load, []);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <div className="flex items-center gap-2 text-sm font-medium text-ink">
          <History size={15} className="text-accent" />
          Recent AI Actions
        </div>
        <button onClick={load} className="text-muted hover:text-ink transition-colors" title="Refresh">
          <RefreshCw size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-2">
        {error && <p className="text-sm text-bad">{error}</p>}
        {!error && logs === null && <p className="text-sm text-muted">Loading…</p>}
        {!error && logs !== null && logs.length === 0 && (
          <p className="text-sm text-muted">No AI activity yet — ask something in one of the tabs.</p>
        )}
        {logs?.map((log) => (
          <div key={log.id} className="rounded-lg border border-border bg-surface-hi px-3 py-2.5">
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="text-xs font-mono text-muted">{log.intent ?? "UNKNOWN"}</span>
              <span className="text-[10px] text-muted whitespace-nowrap">{timeAgo(log.created_at)}</span>
            </div>
            <p className="text-sm text-ink line-clamp-2">{log.message}</p>
            {log.action_status && (
              <span
                className={`inline-block mt-1.5 text-[10px] px-1.5 py-0.5 rounded-full border ${
                  STATUS_STYLES[log.action_status] ?? "bg-surface text-muted border-border"
                }`}
              >
                {log.action_status}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
