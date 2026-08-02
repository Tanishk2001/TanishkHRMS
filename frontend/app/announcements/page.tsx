"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Megaphone, ArrowRight } from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import { listAnnouncements, AnnouncementRow, getRole } from "@/lib/api";

function AnnouncementsContent() {
  const router = useRouter();
  const [rows, setRows] = useState<AnnouncementRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const role = typeof window !== "undefined" ? getRole() : null;
  const canCreate = role === "MANAGER" || role === "ADMIN";

  useEffect(() => {
    listAnnouncements()
      .then(setRows)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-4">
      {canCreate && (
        <button
          onClick={() => router.push("/ai-copilot?tab=action")}
          className="w-full flex items-center justify-center gap-2 bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium rounded-lg py-2.5"
        >
          Post an announcement via the Copilot <ArrowRight size={14} />
        </button>
      )}

      {error && <p className="text-sm text-bad">{error}</p>}
      {rows === null && !error && <p className="text-sm text-muted">Loading…</p>}
      {rows && rows.length === 0 && <p className="text-sm text-muted">No announcements yet.</p>}

      <div className="space-y-3">
        {rows?.map((a) => (
          <div key={a.id} className="bg-surface border border-border rounded-xl p-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center shrink-0">
                <Megaphone size={14} className="text-accent" />
              </div>
              <div>
                <h3 className="font-display font-semibold text-sm text-ink">{a.title}</h3>
                <p className="text-sm text-muted mt-1">{a.body}</p>
                <p className="text-[11px] text-muted font-mono mt-2">
                  {a.created_by_name} · {new Date(a.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AnnouncementsPage() {
  return (
    <DashboardShell title="Announcements">
      <AnnouncementsContent />
    </DashboardShell>
  );
}
