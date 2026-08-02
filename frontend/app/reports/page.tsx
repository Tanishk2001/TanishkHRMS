"use client";

import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line,
} from "recharts";
import { BarChart3, Users, CalendarClock, Fingerprint, Ticket as TicketIcon, AlertTriangle } from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import DashCard from "@/components/layout/dash-card";
import {
  getHeadcountReport, getLeaveTrendsReport, getAttendanceTrendsReport, getTicketsReport,
  HeadcountReport, LeaveTrendsReport, AttendanceTrendsReport, TicketsReport,
} from "@/lib/api";

const COLORS = ["#7C6FF0", "#4ADE80", "#F5A623", "#F87171", "#4C4499"];
const CHART_TEXT = { fill: "#8B87B0", fontSize: 11, fontFamily: "ui-monospace, monospace" };

function ReportsContent() {
  const [headcount, setHeadcount] = useState<HeadcountReport | null>(null);
  const [leaveTrends, setLeaveTrends] = useState<LeaveTrendsReport | null>(null);
  const [attendanceTrends, setAttendanceTrends] = useState<AttendanceTrendsReport | null>(null);
  const [tickets, setTickets] = useState<TicketsReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHeadcountReport().then(setHeadcount).catch((e) => setError(e.message));
    getLeaveTrendsReport().then(setLeaveTrends).catch(() => {});
    getAttendanceTrendsReport().then(setAttendanceTrends).catch(() => {});
    getTicketsReport().then(setTickets).catch(() => {});
  }, []);

  if (error) {
    return <p className="p-6 text-sm text-bad">{error}</p>;
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-surface border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-muted text-xs font-mono mb-2">
            <Users size={13} /> ACTIVE HEADCOUNT
          </div>
          <p className="text-2xl font-mono text-ink">{headcount?.total_active ?? "—"}</p>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-muted text-xs font-mono mb-2">
            <CalendarClock size={13} /> LEAVE REQUESTS (90D)
          </div>
          <p className="text-2xl font-mono text-ink">{leaveTrends?.total_requests_last_90_days ?? "—"}</p>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-muted text-xs font-mono mb-2">
            <Fingerprint size={13} /> LATE RATE (14D)
          </div>
          <p className="text-2xl font-mono text-ink">
            {attendanceTrends ? `${attendanceTrends.late_rate_pct}%` : "—"}
          </p>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-muted text-xs font-mono mb-2">
            <TicketIcon size={13} /> OPEN TICKETS
          </div>
          <p className="text-2xl font-mono text-ink">{tickets?.total_open ?? "—"}</p>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-muted text-xs font-mono mb-2">
            <AlertTriangle size={13} /> SLA BREACHED
          </div>
          <p className={`text-2xl font-mono ${tickets && tickets.total_breached > 0 ? "text-bad" : "text-ink"}`}>
            {tickets?.total_breached ?? "—"}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <DashCard icon={Users} eyebrow="Core HR" title="Headcount by department">
          {headcount ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={headcount.by_department}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2A2650" />
                <XAxis dataKey="department" tick={CHART_TEXT} />
                <YAxis allowDecimals={false} tick={CHART_TEXT} />
                <Tooltip contentStyle={{ background: "#14122B", border: "1px solid #2A2650", borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="headcount" fill="#7C6FF0" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-muted">Loading…</p>
          )}
        </DashCard>

        <DashCard icon={Fingerprint} eyebrow="Attendance" title="Last 14 days">
          {attendanceTrends ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={attendanceTrends.last_14_days}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2A2650" />
                <XAxis dataKey="work_date" tick={CHART_TEXT} tickFormatter={(d) => d.slice(5)} />
                <YAxis allowDecimals={false} tick={CHART_TEXT} />
                <Tooltip contentStyle={{ background: "#14122B", border: "1px solid #2A2650", borderRadius: 8, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="present" stroke="#4ADE80" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="late" stroke="#F5A623" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-muted">Loading…</p>
          )}
        </DashCard>

        <DashCard icon={CalendarClock} eyebrow="Leave" title="Requests by type & status">
          {leaveTrends && leaveTrends.by_type.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={leaveTrends.by_type}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2A2650" />
                <XAxis dataKey="leave_type" tick={CHART_TEXT} />
                <YAxis allowDecimals={false} tick={CHART_TEXT} />
                <Tooltip contentStyle={{ background: "#14122B", border: "1px solid #2A2650", borderRadius: 8, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="approved" stackId="a" fill="#4ADE80" />
                <Bar dataKey="pending" stackId="a" fill="#F5A623" />
                <Bar dataKey="rejected" stackId="a" fill="#F87171" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : leaveTrends ? (
            <p className="text-muted">No leave requests yet.</p>
          ) : (
            <p className="text-muted">Loading…</p>
          )}
        </DashCard>

        <DashCard icon={TicketIcon} eyebrow="Help Desk" title="Tickets by status">
          {tickets && tickets.by_status.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={tickets.by_status} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={75} label>
                  {tickets.by_status.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#14122B", border: "1px solid #2A2650", borderRadius: 8, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : tickets ? (
            <p className="text-muted">No tickets yet.</p>
          ) : (
            <p className="text-muted">Loading…</p>
          )}
        </DashCard>
      </div>
    </div>
  );
}

export default function ReportsPage() {
  return (
    <DashboardShell title="Reports & Analytics">
      <ReportsContent />
    </DashboardShell>
  );
}
