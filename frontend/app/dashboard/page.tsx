"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, CalendarClock, Fingerprint, Megaphone, ScrollText, Sparkles } from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import DashCard from "@/components/layout/dash-card";
import {
  askRouter,
  getLeaveBalance,
  listAnnouncements,
  listPolicies,
  getTodayAttendance,
  checkIn,
  LeaveBalanceRow,
  AnnouncementRow,
  PolicyRow,
  TodayAttendanceStatus,
} from "@/lib/api";

const TAB_BY_INTENT: Record<string, string> = {
  POLICY_QA: "policy",
  SQL_QUERY: "sql",
  HR_ACTION: "action",
  UNKNOWN: "policy",
};

function DashboardContent() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [routing, setRouting] = useState(false);

  const [balances, setBalances] = useState<LeaveBalanceRow[] | null>(null);
  const [announcements, setAnnouncements] = useState<AnnouncementRow[] | null>(null);
  const [policies, setPolicies] = useState<PolicyRow[] | null>(null);
  const [attendance, setAttendance] = useState<TodayAttendanceStatus | null>(null);
  const [checkingIn, setCheckingIn] = useState(false);

  useEffect(() => {
    getLeaveBalance().then(setBalances).catch(() => setBalances([]));
    listAnnouncements().then(setAnnouncements).catch(() => setAnnouncements([]));
    listPolicies().then(setPolicies).catch(() => setPolicies([]));
    getTodayAttendance().then(setAttendance).catch(() => setAttendance(null));
  }, []);

  async function handleQuickCheckIn() {
    setCheckingIn(true);
    try {
      await checkIn();
      getTodayAttendance().then(setAttendance);
    } catch {
      // surfaced implicitly by the button staying in its "not checked in" state
    } finally {
      setCheckingIn(false);
    }
  }

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || routing) return;
    setRouting(true);
    try {
      const res = await askRouter(query);
      const tab = TAB_BY_INTENT[res.data?.intent ?? "UNKNOWN"] ?? "policy";
      router.push(`/ai-copilot?tab=${tab}&q=${encodeURIComponent(query)}`);
    } catch {
      router.push(`/ai-copilot?tab=policy&q=${encodeURIComponent(query)}`);
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      {/* Signature: the copilot is the primary interaction, not a buried tab */}
      <form onSubmit={handleAsk} className="relative">
        <div className="absolute inset-0 bg-accent/20 blur-2xl rounded-2xl pointer-events-none" />
        <div className="relative flex items-center gap-3 bg-surface border border-accent/40 rounded-2xl px-5 py-4 shadow-glow">
          <Sparkles size={18} className="text-accent shrink-0" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask the Copilot — try “How many sick leaves do I get?” or “Apply casual leave for tomorrow.”"
            className="flex-1 bg-transparent outline-none text-sm placeholder:text-muted"
          />
          <button
            type="submit"
            disabled={routing}
            className="flex items-center gap-1.5 text-xs font-medium bg-accent hover:bg-accent/90 transition-colors text-white rounded-lg px-3.5 py-2 disabled:opacity-50"
          >
            {routing ? "Routing…" : "Ask"}
            <ArrowRight size={13} />
          </button>
        </div>
      </form>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <DashCard
          icon={Fingerprint}
          eyebrow="Today"
          title="Attendance"
          footer={
            <button
              onClick={() => router.push("/attendance")}
              className="text-xs font-medium text-accent flex items-center gap-1 hover:gap-1.5 transition-all"
            >
              View history <ArrowRight size={12} />
            </button>
          }
        >
          {attendance === null ? (
            <p className="text-muted">Loading…</p>
          ) : attendance.checked_in ? (
            <p>
              Checked in at{" "}
              <span className="text-ink font-mono">
                {new Date(attendance.check_in_at!).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
              {attendance.status === "LATE" && <span className="text-warn"> · LATE</span>}
              {attendance.checked_out && <span className="block mt-1 text-ink">Checked out for the day.</span>}
            </p>
          ) : (
            <button
              onClick={handleQuickCheckIn}
              disabled={checkingIn}
              className="w-full bg-accent hover:bg-accent/90 transition-colors text-white text-xs font-medium rounded-lg py-2 disabled:opacity-50"
            >
              {checkingIn ? "Checking in…" : "Check in now"}
            </button>
          )}
        </DashCard>

        <DashCard
          icon={CalendarClock}
          eyebrow="Leave"
          title="Your leave balance"
          footer={
            <button
              onClick={() => router.push("/ai-copilot?tab=action")}
              className="text-xs font-medium text-accent flex items-center gap-1 hover:gap-1.5 transition-all"
            >
              Open leave assistant <ArrowRight size={12} />
            </button>
          }
        >
          {balances === null ? (
            <p className="text-muted">Loading…</p>
          ) : (
            <ul className="space-y-1.5 font-mono text-xs">
              {balances.map((b) => (
                <li key={b.leave_type} className="flex justify-between">
                  <span className="text-ink">{b.leave_type}</span>
                  <span>{b.balance_days} days</span>
                </li>
              ))}
            </ul>
          )}
        </DashCard>

        <DashCard
          icon={Megaphone}
          eyebrow="Company"
          title="Recent announcements"
          footer={
            <button
              onClick={() => router.push("/announcements")}
              className="text-xs font-medium text-accent flex items-center gap-1 hover:gap-1.5 transition-all"
            >
              View all <ArrowRight size={12} />
            </button>
          }
        >
          {announcements === null ? (
            <p className="text-muted">Loading…</p>
          ) : announcements.length === 0 ? (
            <p className="text-muted">No announcements yet.</p>
          ) : (
            <ul className="space-y-2">
              {announcements.slice(0, 3).map((a) => (
                <li key={a.id} className="text-ink text-[13px] leading-snug">
                  {a.title}
                </li>
              ))}
            </ul>
          )}
        </DashCard>

        <DashCard
          icon={ScrollText}
          eyebrow="Reference"
          title="HR policies"
          footer={
            <button
              onClick={() => router.push("/ai-copilot?tab=policy")}
              className="text-xs font-medium text-accent flex items-center gap-1 hover:gap-1.5 transition-all"
            >
              Ask about a policy <ArrowRight size={12} />
            </button>
          }
        >
          {policies === null ? (
            <p className="text-muted">Loading…</p>
          ) : (
            <p>
              <span className="text-ink font-mono">{policies.length}</span> policies on file across{" "}
              <span className="text-ink font-mono">
                {new Set(policies.map((p) => p.category)).size}
              </span>{" "}
              categories.
            </p>
          )}
        </DashCard>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <DashboardShell title="Dashboard">
      <DashboardContent />
    </DashboardShell>
  );
}
