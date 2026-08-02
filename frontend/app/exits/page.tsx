"use client";

import { useEffect, useState } from "react";
import { DoorOpen, Check, X, ClipboardCheck } from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import {
  submitResignation, getMyExitRequests, listExitRequests,
  decideExitRequest, updateExitChecklist, completeExit,
  ExitRequestRow, getRole,
} from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  PENDING: "text-warn",
  APPROVED: "text-accent",
  REJECTED: "text-bad",
  COMPLETED: "text-good",
};

function ChecklistLine({ label, done }: { label: string; done: boolean }) {
  return (
    <span className={`flex items-center gap-1 text-xs ${done ? "text-good" : "text-muted"}`}>
      {done ? <Check size={12} /> : <X size={12} />} {label}
    </span>
  );
}

function ExitsContent() {
  const role = typeof window !== "undefined" ? getRole() : null;
  const canDecide = role === "MANAGER" || role === "ADMIN";
  const isAdmin = role === "ADMIN";

  const [requests, setRequests] = useState<ExitRequestRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lwd, setLwd] = useState("");
  const [reason, setReason] = useState("");
  const [showForm, setShowForm] = useState(false);

  function refresh() {
    const loader = canDecide ? listExitRequests() : getMyExitRequests();
    loader.then(setRequests).catch((e) => setError(e.message));
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await submitResignation(lwd, reason || undefined);
      setShowForm(false);
      setLwd("");
      setReason("");
      refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleDecision(id: number, decision: "APPROVED" | "REJECTED") {
    try {
      await decideExitRequest(id, decision);
      refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleChecklistToggle(req: ExitRequestRow, field: "knowledge_transfer_done" | "exit_interview_done" | "fnf_settled") {
    try {
      await updateExitChecklist(req.id, { [field]: !req[field] });
      refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleComplete(id: number) {
    try {
      await completeExit(id);
      refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-4">
      {!canDecide && (
        <div>
          {!showForm ? (
            <button
              onClick={() => setShowForm(true)}
              className="w-full flex items-center justify-center gap-2 bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium rounded-lg py-2.5"
            >
              <DoorOpen size={14} /> Submit resignation
            </button>
          ) : (
            <form onSubmit={handleSubmit} className="bg-surface border border-border rounded-xl p-4 space-y-3">
              <div>
                <label className="block text-xs text-muted mb-1">Last working day</label>
                <input type="date" value={lwd} onChange={(e) => setLwd(e.target.value)} required
                       className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent" />
              </div>
              <div>
                <label className="block text-xs text-muted mb-1">Reason (optional)</label>
                <input value={reason} onChange={(e) => setReason(e.target.value)}
                       className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent" />
              </div>
              <div className="flex gap-2">
                <button type="submit" className="bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium rounded-lg px-4 py-1.5">
                  Submit
                </button>
                <button type="button" onClick={() => setShowForm(false)} className="text-sm text-muted hover:text-ink">
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {error && <p className="text-sm text-bad">{error}</p>}
      {requests === null && !error && <p className="text-sm text-muted">Loading…</p>}
      {requests && requests.length === 0 && <p className="text-sm text-muted">No exit requests.</p>}

      <div className="space-y-3">
        {requests?.map((r) => (
          <div key={r.id} className="bg-surface border border-border rounded-xl p-4">
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className="text-sm text-ink font-medium">{r.employee_name}</p>
                <p className="text-[11px] text-muted font-mono">Last day: {r.last_working_day}</p>
                {r.reason && <p className="text-xs text-muted mt-1">{r.reason}</p>}
              </div>
              <span className={`text-xs font-mono font-medium ${STATUS_STYLES[r.status] ?? "text-muted"}`}>
                {r.status}
              </span>
            </div>

            {canDecide && r.status === "PENDING" && (
              <div className="flex gap-2 mt-2">
                <button onClick={() => handleDecision(r.id, "APPROVED")}
                        className="text-xs font-medium text-good hover:underline">Approve</button>
                <button onClick={() => handleDecision(r.id, "REJECTED")}
                        className="text-xs font-medium text-bad hover:underline">Reject</button>
              </div>
            )}

            {r.status === "APPROVED" && (
              <div className="mt-3 pt-3 border-t border-border">
                <div className="flex items-center gap-2 mb-2">
                  <ClipboardCheck size={13} className="text-accent" />
                  <span className="text-xs font-medium text-ink">Offboarding checklist</span>
                </div>
                <div className="flex flex-wrap gap-3 mb-2">
                  {isAdmin ? (
                    <>
                      <button onClick={() => handleChecklistToggle(r, "knowledge_transfer_done")}>
                        <ChecklistLine label="Knowledge transfer" done={r.knowledge_transfer_done} />
                      </button>
                      <button onClick={() => handleChecklistToggle(r, "exit_interview_done")}>
                        <ChecklistLine label="Exit interview" done={r.exit_interview_done} />
                      </button>
                      <button onClick={() => handleChecklistToggle(r, "fnf_settled")}>
                        <ChecklistLine label="F&F settled" done={r.fnf_settled} />
                      </button>
                    </>
                  ) : (
                    <>
                      <ChecklistLine label="Knowledge transfer" done={r.knowledge_transfer_done} />
                      <ChecklistLine label="Exit interview" done={r.exit_interview_done} />
                      <ChecklistLine label="F&F settled" done={r.fnf_settled} />
                    </>
                  )}
                  <ChecklistLine label="Assets returned" done={r.assets_returned} />
                </div>
                {isAdmin && (
                  <button
                    onClick={() => handleComplete(r.id)}
                    className="text-xs font-medium bg-accent hover:bg-accent/90 transition-colors text-white rounded-lg px-3 py-1.5"
                  >
                    Complete offboarding
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ExitsPage() {
  return (
    <DashboardShell title="Exit Management">
      <ExitsContent />
    </DashboardShell>
  );
}
