"use client";

import { useEffect, useState } from "react";
import { Clock, Plus, Trash2 } from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import {
  getMyProjects, getMyTimeEntries, logTime, deleteTimeEntry, getTeamTimeEntries,
  MyProjectRow, TimeEntryRow, TeamTimeEntryRow, getRole,
} from "@/lib/api";

function EntriesTable({ rows, onDelete }: { rows: TimeEntryRow[]; onDelete?: (id: number) => void }) {
  const totalHours = rows.reduce((sum, r) => sum + r.hours, 0);
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-muted text-xs font-mono">
            <th className="pb-2 font-medium">Date</th>
            <th className="pb-2 font-medium">Project</th>
            <th className="pb-2 font-medium">Hours</th>
            <th className="pb-2 font-medium">Type</th>
            <th className="pb-2 font-medium">Notes</th>
            {onDelete && <th className="pb-2"></th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((e) => (
            <tr key={e.id} className="border-t border-border">
              <td className="py-2 text-ink">{e.work_date}</td>
              <td className="py-2 text-muted">{e.project_name}</td>
              <td className="py-2 text-ink font-mono">{e.hours}h</td>
              <td className="py-2">
                <span className={`text-xs font-mono ${e.billable ? "text-good" : "text-muted"}`}>
                  {e.billable ? "Billable" : "Non-billable"}
                </span>
              </td>
              <td className="py-2 text-muted text-xs">{e.description ?? "—"}</td>
              {onDelete && (
                <td className="py-2">
                  <button onClick={() => onDelete(e.id)}>
                    <Trash2 size={13} className="text-muted hover:text-bad" />
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-muted font-mono mt-2">Total: {totalHours}h</p>
    </div>
  );
}

function TimeTrackingContent() {
  const role = typeof window !== "undefined" ? getRole() : null;
  const canViewTeam = role === "MANAGER" || role === "ADMIN";

  const [projects, setProjects] = useState<MyProjectRow[] | null>(null);
  const [entries, setEntries] = useState<TimeEntryRow[] | null>(null);
  const [team, setTeam] = useState<TeamTimeEntryRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [projectId, setProjectId] = useState("");
  const [workDate, setWorkDate] = useState(new Date().toISOString().slice(0, 10));
  const [hours, setHours] = useState("");
  const [billable, setBillable] = useState(true);
  const [description, setDescription] = useState("");

  function refresh() {
    getMyProjects().then(setProjects).catch(() => setProjects([]));
    getMyTimeEntries().then(setEntries).catch((e) => setError(e.message));
    if (canViewTeam) getTeamTimeEntries().then(setTeam).catch(() => {});
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !hours) return;
    try {
      await logTime(Number(projectId), workDate, Number(hours), billable, description || undefined);
      setShowForm(false);
      setHours("");
      setDescription("");
      refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteTimeEntry(id);
      refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex justify-end">
        <button
          onClick={() => setShowForm((s) => !s)}
          className="flex items-center gap-1.5 text-xs font-medium bg-accent hover:bg-accent/90 transition-colors text-white rounded-lg px-3 py-2"
        >
          <Plus size={13} /> Log time
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-surface border border-border rounded-xl p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-muted mb-1">Project</label>
              <select
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                required
                className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent"
              >
                <option value="">Select project…</option>
                {projects?.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              {projects?.length === 0 && (
                <p className="text-xs text-muted mt-1">You&rsquo;re not assigned to any projects yet.</p>
              )}
            </div>
            <div>
              <label className="block text-xs text-muted mb-1">Date</label>
              <input type="date" value={workDate} onChange={(e) => setWorkDate(e.target.value)} required
                     className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent" />
            </div>
            <div>
              <label className="block text-xs text-muted mb-1">Hours</label>
              <input type="number" step="0.5" min="0.5" max="24" value={hours} onChange={(e) => setHours(e.target.value)} required
                     className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent" />
            </div>
            <div>
              <label className="block text-xs text-muted mb-1">Type</label>
              <select
                value={billable ? "billable" : "non-billable"}
                onChange={(e) => setBillable(e.target.value === "billable")}
                className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent"
              >
                <option value="billable">Billable</option>
                <option value="non-billable">Non-billable</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-muted mb-1">Notes (optional)</label>
            <input value={description} onChange={(e) => setDescription(e.target.value)}
                   className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent" />
          </div>
          <div className="flex justify-end">
            <button type="submit" className="bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium rounded-lg px-4 py-1.5">
              Save entry
            </button>
          </div>
        </form>
      )}

      {error && <p className="text-sm text-bad">{error}</p>}

      <div className="bg-surface border border-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Clock size={16} className="text-accent" />
          <h2 className="font-display font-semibold text-[15px]">Your recent entries</h2>
        </div>
        {entries === null && !error && <p className="text-sm text-muted">Loading…</p>}
        {entries?.length === 0 && <p className="text-sm text-muted">No time logged in the last 14 days.</p>}
        {entries && entries.length > 0 && <EntriesTable rows={entries} onDelete={handleDelete} />}
      </div>

      {canViewTeam && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="font-display font-semibold text-[15px] mb-4">Team — last 7 days</h2>
          {team === null && <p className="text-sm text-muted">Loading…</p>}
          {team?.length === 0 && <p className="text-sm text-muted">No team time entries yet.</p>}
          {team && team.length > 0 && (
            <div className="space-y-1">
              {team.map((e) => (
                <div key={e.id} className="flex items-center justify-between text-sm py-1.5 border-t border-border first:border-t-0">
                  <span className="text-ink">{e.employee_name}</span>
                  <span className="text-muted text-xs">{e.project_name}</span>
                  <span className="text-xs text-muted font-mono">{e.work_date}</span>
                  <span className="text-ink font-mono text-xs">{e.hours}h</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function TimeTrackingPage() {
  return (
    <DashboardShell title="Time Tracking">
      <TimeTrackingContent />
    </DashboardShell>
  );
}
