"use client";

import { useEffect, useState } from "react";
import { Fingerprint, LogIn, LogOut, Users } from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import {
  getTodayAttendance, checkIn, checkOut, getMyAttendanceHistory, getTeamAttendance,
  TodayAttendanceStatus, AttendanceHistoryRow, TeamAttendanceRow, getRole,
} from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  PRESENT: "text-good",
  LATE: "text-warn",
  ABSENT: "text-bad",
};

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function AttendanceContent() {
  const role = typeof window !== "undefined" ? getRole() : null;
  const canViewTeam = role === "MANAGER" || role === "ADMIN";

  const [today, setToday] = useState<TodayAttendanceStatus | null>(null);
  const [history, setHistory] = useState<AttendanceHistoryRow[] | null>(null);
  const [team, setTeam] = useState<TeamAttendanceRow[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    getTodayAttendance().then(setToday).catch(() => {});
    getMyAttendanceHistory().then(setHistory).catch(() => {});
    if (canViewTeam) getTeamAttendance().then(setTeam).catch(() => {});
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCheckIn() {
    setBusy(true);
    setError(null);
    try {
      await checkIn();
      refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleCheckOut() {
    setBusy(true);
    setError(null);
    try {
      await checkOut();
      refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="bg-surface border border-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Fingerprint size={16} className="text-accent" />
          <h2 className="font-display font-semibold text-[15px]">Today</h2>
          {today?.status && (
            <span className={`ml-auto text-xs font-mono font-medium ${STATUS_STYLES[today.status] ?? "text-muted"}`}>
              {today.status}
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-base border border-border rounded-lg p-4">
            <p className="text-[11px] uppercase tracking-widest text-muted font-mono mb-1">Check-in</p>
            <p className="text-lg font-mono text-ink">{fmtTime(today?.check_in_at ?? null)}</p>
          </div>
          <div className="bg-base border border-border rounded-lg p-4">
            <p className="text-[11px] uppercase tracking-widest text-muted font-mono mb-1">Check-out</p>
            <p className="text-lg font-mono text-ink">{fmtTime(today?.check_out_at ?? null)}</p>
          </div>
        </div>

        {error && <p className="text-sm text-bad mb-3">{error}</p>}

        <div className="flex gap-2">
          <button
            onClick={handleCheckIn}
            disabled={busy || !!today?.checked_in}
            className="flex-1 flex items-center justify-center gap-2 bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium rounded-lg py-2.5 disabled:opacity-40"
          >
            <LogIn size={14} /> Check in
          </button>
          <button
            onClick={handleCheckOut}
            disabled={busy || !today?.checked_in || !!today?.checked_out}
            className="flex-1 flex items-center justify-center gap-2 border border-border hover:bg-surface-hi transition-colors text-ink text-sm font-medium rounded-lg py-2.5 disabled:opacity-40"
          >
            <LogOut size={14} /> Check out
          </button>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="font-display font-semibold text-[15px] mb-3">Recent history</h2>
        {history === null ? (
          <p className="text-sm text-muted">Loading…</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-muted text-xs font-mono">
                  <th className="pb-2 font-medium">Date</th>
                  <th className="pb-2 font-medium">Check-in</th>
                  <th className="pb-2 font-medium">Check-out</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id} className="border-t border-border">
                    <td className="py-2 text-ink">{h.work_date}</td>
                    <td className="py-2 text-muted font-mono text-xs">{fmtTime(h.check_in_at)}</td>
                    <td className="py-2 text-muted font-mono text-xs">{fmtTime(h.check_out_at)}</td>
                    <td className={`py-2 font-mono text-xs font-medium ${STATUS_STYLES[h.status] ?? "text-muted"}`}>
                      {h.status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {canViewTeam && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Users size={15} className="text-accent" />
            <h2 className="font-display font-semibold text-[15px]">Team — today</h2>
          </div>
          {team === null ? (
            <p className="text-sm text-muted">Loading…</p>
          ) : team.length === 0 ? (
            <p className="text-sm text-muted">No attendance recorded yet today.</p>
          ) : (
            <div className="space-y-2">
              {team.map((t) => (
                <div key={t.employee_id} className="flex items-center justify-between text-sm">
                  <span className="text-ink">{t.employee_name}</span>
                  <span className="flex items-center gap-3 text-xs font-mono text-muted">
                    {fmtTime(t.check_in_at)} – {fmtTime(t.check_out_at)}
                    <span className={STATUS_STYLES[t.status] ?? "text-muted"}>{t.status}</span>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AttendancePage() {
  return (
    <DashboardShell title="Attendance">
      <AttendanceContent />
    </DashboardShell>
  );
}
