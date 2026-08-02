"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ScrollText, ArrowRight } from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import { listPolicies, PolicyRow } from "@/lib/api";

function PoliciesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const query = (searchParams.get("q") ?? "").toLowerCase().trim();

  const [rows, setRows] = useState<PolicyRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    listPolicies()
      .then(setRows)
      .catch((e) => setError(e.message));
  }, []);

  const filtered = rows?.filter((p) => {
    if (!query) return true;
    return (
      p.title.toLowerCase().includes(query) ||
      p.category.toLowerCase().includes(query) ||
      p.content.toLowerCase().includes(query)
    );
  });

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-4">
      <button
        onClick={() => router.push("/ai-copilot?tab=policy")}
        className="w-full flex items-center justify-center gap-2 bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium rounded-lg py-2.5"
      >
        Ask the Copilot a policy question <ArrowRight size={14} />
      </button>

      {error && <p className="text-sm text-bad">{error}</p>}
      {rows === null && !error && <p className="text-sm text-muted">Loading…</p>}
      {filtered && filtered.length === 0 && (
        <p className="text-sm text-muted">No policies match &ldquo;{query}&rdquo;.</p>
      )}

      <div className="space-y-2">
        {filtered?.map((p) => (
          <div key={p.id} className="bg-surface border border-border rounded-xl overflow-hidden">
            <button
              onClick={() => setExpanded(expanded === p.id ? null : p.id)}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-surface-hi transition-colors"
            >
              <ScrollText size={14} className="text-accent shrink-0" />
              <span className="font-medium text-sm text-ink">{p.title}</span>
              <span className="ml-auto text-[10px] uppercase tracking-widest text-muted font-mono">
                {p.category}
              </span>
            </button>
            {expanded === p.id && (
              <div className="px-4 pb-4 pt-1 text-sm text-muted whitespace-pre-line border-t border-border">
                {p.content}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PoliciesPage() {
  return (
    <DashboardShell title="HR Policies">
      <Suspense fallback={null}>
        <PoliciesContent />
      </Suspense>
    </DashboardShell>
  );
}
