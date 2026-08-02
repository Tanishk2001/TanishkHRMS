"use client";

import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import { Activity, ShieldAlert, Timer, Database, MessageSquareWarning } from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import DashCard from "@/components/layout/dash-card";
import { getAiUsageStats, getRole, AIUsageStats } from "@/lib/api";

const COLORS = ["#7C6FF0", "#4ADE80", "#F5A623", "#F87171", "#4C4499"];
const CHART_TEXT = { fill: "#8B87B0", fontSize: 11, fontFamily: "ui-monospace, monospace" };

function toChartRows(record: Record<string, number>) {
  return Object.entries(record).map(([name, count]) => ({ name, count }));
}

function UsageDashboardContent() {
  const [stats, setStats] = useState<AIUsageStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const role = typeof window !== "undefined" ? getRole() : null;

  useEffect(() => {
    if (role !== "ADMIN") return;
    getAiUsageStats()
      .then((res) => setStats(res.data))
      .catch((e) => setError(e.message));
  }, [role]);

  if (role !== "ADMIN") {
    return (
      <p className="p-6 text-sm text-muted">
        The AI usage dashboard is an admin-only surface — the same way company-wide analytics is.
      </p>
    );
  }

  if (error) {
    return <p className="p-6 text-sm text-bad">{error}</p>;
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-surface border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-muted text-xs font-mono mb-2">
            <Activity size={13} /> TOTAL AI REQUESTS
          </div>
          <p className="text-2xl font-mono text-ink">{stats?.total_requests ?? "—"}</p>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-muted text-xs font-mono mb-2">
            <ShieldAlert size={13} /> FAILED PERMISSION ATTEMPTS
          </div>
          <p className="text-2xl font-mono text-ink">{stats?.failed_permission_attempts ?? "—"}</p>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-muted text-xs font-mono mb-2">
            <Timer size={13} /> AVG RESPONSE LATENCY
          </div>
          <p className="text-2xl font-mono text-ink">
            {stats?.avg_latency_ms != null ? `${stats.avg_latency_ms}ms` : "—"}
          </p>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 text-muted text-xs font-mono mb-2">
            <Database size={13} /> SQL QUERIES BLOCKED
          </div>
          <p className="text-2xl font-mono text-ink">{stats?.sql_blocked_count ?? "—"}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <DashCard icon={Activity} eyebrow="Router" title="Requests by intent">
          {stats && Object.keys(stats.requests_by_intent).length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={toChartRows(stats.requests_by_intent)}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={75}
                  label
                >
                  {toChartRows(stats.requests_by_intent).map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#14122B", border: "1px solid #2A2650", borderRadius: 8, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-muted">{stats ? "No AI activity yet." : "Loading…"}</p>
          )}
        </DashCard>

        <DashCard icon={Database} eyebrow="Tools" title="Requests by tool/agent">
          {stats && Object.keys(stats.requests_by_tool).length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={toChartRows(stats.requests_by_tool)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2A2650" />
                <XAxis dataKey="name" tick={CHART_TEXT} />
                <YAxis allowDecimals={false} tick={CHART_TEXT} />
                <Tooltip contentStyle={{ background: "#14122B", border: "1px solid #2A2650", borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="count" fill="#7C6FF0" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-muted">{stats ? "No AI activity yet." : "Loading…"}</p>
          )}
        </DashCard>

        <DashCard icon={MessageSquareWarning} eyebrow="Policy RAG" title="No-answer rate">
          <div className="flex flex-col gap-2">
            <p className="text-2xl font-mono text-ink">
              {stats?.rag_no_answer_rate_pct != null ? `${stats.rag_no_answer_rate_pct}%` : "—"}
            </p>
            <p className="text-xs text-muted">
              {stats?.rag_no_answer_count ?? 0} policy question(s) had insufficient context to answer —
              a healthy sign the assistant refuses rather than guesses.
            </p>
          </div>
        </DashCard>

        <DashCard icon={ShieldAlert} eyebrow="Guardrails" title="What these numbers mean">
          <ul className="text-xs text-muted space-y-1.5 list-disc pl-4">
            <li>Failed permission attempts = AI-layer refusals (DENIED), not app errors.</li>
            <li>SQL blocked = read-only guardrail or RBAC denial before any query ran.</li>
            <li>Latency is measured server-side per request across all three agents.</li>
          </ul>
        </DashCard>
      </div>
    </div>
  );
}

export default function AIUsageDashboardPage() {
  return (
    <DashboardShell title="AI Usage Dashboard">
      <UsageDashboardContent />
    </DashboardShell>
  );
}
