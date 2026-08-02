"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Ticket as TicketIcon, Plus, MessageSquare, AlertTriangle, ChevronDown, ChevronUp,
} from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import {
  listMyTickets, listAllTickets, createTicket, updateTicket,
  listTicketComments, addTicketComment,
  getRole, TicketRow, TicketDetail, TicketCommentRow,
} from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  OPEN: "text-warn",
  IN_PROGRESS: "text-accent",
  CLOSED: "text-good",
};

const CATEGORY_STYLES: Record<string, string> = {
  HR: "bg-purple-500/15 text-purple-400",
  IT: "bg-blue-500/15 text-blue-400",
  ADMIN: "bg-amber-500/15 text-amber-400",
  FINANCE: "bg-emerald-500/15 text-emerald-400",
};

function CategoryBadge({ category }: { category: string }) {
  return (
    <span className={`text-[10px] font-mono font-medium px-2 py-0.5 rounded ${CATEGORY_STYLES[category] ?? "bg-muted/15 text-muted"}`}>
      {category}
    </span>
  );
}

function SlaBadge({ slaDueAt, breached }: { slaDueAt: string | null; breached: boolean }) {
  if (!slaDueAt) return null;
  if (breached) {
    return (
      <span className="flex items-center gap-1 text-[10px] font-mono font-medium text-bad">
        <AlertTriangle size={11} /> SLA BREACHED
      </span>
    );
  }
  return (
    <span className="text-[10px] font-mono text-muted">
      due {new Date(slaDueAt).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
    </span>
  );
}

function NewTicketForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("IT");
  const [priority, setPriority] = useState("MEDIUM");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!title.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await createTicket({ title: title.trim(), description: description.trim() || undefined, category, priority });
      setTitle("");
      setDescription("");
      setCategory("IT");
      setPriority("MEDIUM");
      setOpen(false);
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create ticket");
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full flex items-center justify-center gap-2 bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium rounded-lg py-2.5"
      >
        <Plus size={14} /> Raise a ticket
      </button>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-4 space-y-3">
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Short summary of the issue"
        className="w-full bg-base border border-border rounded-lg px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:border-accent"
      />
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Details (optional)"
        rows={2}
        className="w-full bg-base border border-border rounded-lg px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:border-accent resize-none"
      />
      <div className="flex items-center gap-2">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="bg-base border border-border rounded-lg px-2 py-1.5 text-xs text-ink font-mono focus:outline-none focus:border-accent"
        >
          {["HR", "IT", "ADMIN", "FINANCE"].map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
          className="bg-base border border-border rounded-lg px-2 py-1.5 text-xs text-ink font-mono focus:outline-none focus:border-accent"
        >
          {["LOW", "MEDIUM", "HIGH"].map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <div className="flex-1" />
        <button onClick={() => setOpen(false)} className="text-xs text-muted px-3 py-1.5">Cancel</button>
        <button
          onClick={submit}
          disabled={submitting || !title.trim()}
          className="bg-accent hover:bg-accent/90 disabled:opacity-50 transition-colors text-white text-xs font-medium rounded-lg px-4 py-1.5"
        >
          {submitting ? "Submitting…" : "Submit"}
        </button>
      </div>
      {error && <p className="text-xs text-bad">{error}</p>}
    </div>
  );
}

function CommentThread({ ticketId }: { ticketId: number }) {
  const [comments, setComments] = useState<TicketCommentRow[] | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);

  const load = useCallback(() => {
    listTicketComments(ticketId).then(setComments).catch(() => setComments([]));
  }, [ticketId]);

  useEffect(() => { load(); }, [load]);

  async function send() {
    if (!draft.trim()) return;
    setSending(true);
    try {
      await addTicketComment(ticketId, draft.trim());
      setDraft("");
      load();
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="border-t border-border bg-base/40 p-4 space-y-3">
      {comments === null && <p className="text-xs text-muted">Loading comments…</p>}
      {comments && comments.length === 0 && <p className="text-xs text-muted">No comments yet.</p>}
      {comments?.map((c) => (
        <div key={c.id} className="text-xs">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="font-medium text-ink">{c.employee_name}</span>
            <span className="text-muted font-mono">{new Date(c.created_at).toLocaleString()}</span>
          </div>
          <p className="text-muted">{c.body}</p>
        </div>
      ))}
      <div className="flex items-center gap-2 pt-1">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") send(); }}
          placeholder="Add a comment…"
          className="flex-1 bg-base border border-border rounded-lg px-3 py-1.5 text-xs text-ink placeholder:text-muted focus:outline-none focus:border-accent"
        />
        <button
          onClick={send}
          disabled={sending || !draft.trim()}
          className="bg-accent hover:bg-accent/90 disabled:opacity-50 transition-colors text-white text-xs font-medium rounded-lg px-3 py-1.5"
        >
          Send
        </button>
      </div>
    </div>
  );
}

function ManageControls({ ticket, onUpdated }: { ticket: TicketDetail; onUpdated: () => void }) {
  async function set(field: "status" | "priority", value: string) {
    await updateTicket(ticket.id, { [field]: value });
    onUpdated();
  }

  return (
    <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
      <select
        value={ticket.status}
        onChange={(e) => set("status", e.target.value)}
        className="bg-base border border-border rounded-lg px-2 py-1 text-[11px] font-mono text-ink focus:outline-none focus:border-accent"
      >
        {["OPEN", "IN_PROGRESS", "CLOSED"].map((s) => <option key={s} value={s}>{s}</option>)}
      </select>
      <select
        value={ticket.priority}
        onChange={(e) => set("priority", e.target.value)}
        className="bg-base border border-border rounded-lg px-2 py-1 text-[11px] font-mono text-ink focus:outline-none focus:border-accent"
      >
        {["LOW", "MEDIUM", "HIGH"].map((p) => <option key={p} value={p}>{p}</option>)}
      </select>
    </div>
  );
}

function TicketsContent() {
  const role = getRole();
  const canManage = role === "MANAGER" || role === "ADMIN";

  const [tab, setTab] = useState<"mine" | "manage">("mine");
  const [myRows, setMyRows] = useState<TicketRow[] | null>(null);
  const [allRows, setAllRows] = useState<TicketDetail[] | null>(null);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [breachedOnly, setBreachedOnly] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadMine = useCallback(() => {
    listMyTickets().then(setMyRows).catch((e) => setError(e.message));
  }, []);

  const loadAll = useCallback(() => {
    listAllTickets({ category: categoryFilter || undefined, breachedOnly }).then(setAllRows).catch((e) => setError(e.message));
  }, [categoryFilter, breachedOnly]);

  useEffect(() => { loadMine(); }, [loadMine]);
  useEffect(() => { if (canManage) loadAll(); }, [canManage, loadAll]);

  const refreshBoth = () => { loadMine(); if (canManage) loadAll(); };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-4">
      <NewTicketForm onCreated={refreshBoth} />

      {canManage && (
        <div className="flex items-center gap-1 bg-surface border border-border rounded-lg p-1 w-fit">
          <button
            onClick={() => setTab("mine")}
            className={`text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${tab === "mine" ? "bg-accent text-white" : "text-muted"}`}
          >
            My Tickets
          </button>
          <button
            onClick={() => setTab("manage")}
            className={`text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${tab === "manage" ? "bg-accent text-white" : "text-muted"}`}
          >
            Manage Queue
          </button>
        </div>
      )}

      {error && <p className="text-sm text-bad">{error}</p>}

      {tab === "mine" && (
        <>
          {myRows === null && !error && <p className="text-sm text-muted">Loading…</p>}
          {myRows && myRows.length === 0 && <p className="text-sm text-muted">You haven&rsquo;t raised any tickets yet.</p>}
          <div className="space-y-2">
            {myRows?.map((t) => (
              <div key={t.id} className="bg-surface border border-border rounded-xl overflow-hidden">
                <div
                  className="p-4 flex items-center gap-3 cursor-pointer"
                  onClick={() => setExpanded(expanded === t.id ? null : t.id)}
                >
                  <div className="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center shrink-0">
                    <TicketIcon size={14} className="text-accent" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-ink truncate">{t.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <CategoryBadge category={t.category} />
                      <SlaBadge slaDueAt={t.sla_due_at} breached={t.is_breached} />
                    </div>
                  </div>
                  <span className="text-xs font-mono text-muted">{t.priority}</span>
                  <span className={`text-xs font-mono font-medium ${STATUS_STYLES[t.status] ?? "text-muted"}`}>
                    {t.status}
                  </span>
                  <MessageSquare size={14} className="text-muted shrink-0" />
                  {expanded === t.id ? <ChevronUp size={14} className="text-muted shrink-0" /> : <ChevronDown size={14} className="text-muted shrink-0" />}
                </div>
                {expanded === t.id && <CommentThread ticketId={t.id} />}
              </div>
            ))}
          </div>
        </>
      )}

      {tab === "manage" && canManage && (
        <>
          <div className="flex items-center gap-2">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-surface border border-border rounded-lg px-2 py-1.5 text-xs text-ink font-mono focus:outline-none focus:border-accent"
            >
              <option value="">All categories</option>
              {["HR", "IT", "ADMIN", "FINANCE"].map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <button
              onClick={() => setBreachedOnly((v) => !v)}
              className={`flex items-center gap-1 text-xs font-mono px-3 py-1.5 rounded-lg border transition-colors ${
                breachedOnly ? "bg-bad/15 border-bad text-bad" : "bg-surface border-border text-muted"
              }`}
            >
              <AlertTriangle size={12} /> Breached only
            </button>
          </div>

          {allRows === null && !error && <p className="text-sm text-muted">Loading…</p>}
          {allRows && allRows.length === 0 && <p className="text-sm text-muted">No tickets match this filter.</p>}
          <div className="space-y-2">
            {allRows?.map((t) => (
              <div key={t.id} className="bg-surface border border-border rounded-xl overflow-hidden">
                <div
                  className="p-4 flex items-center gap-3 cursor-pointer"
                  onClick={() => setExpanded(expanded === t.id ? null : t.id)}
                >
                  <div className="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center shrink-0">
                    <TicketIcon size={14} className="text-accent" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-ink truncate">{t.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <CategoryBadge category={t.category} />
                      <span className="text-[11px] text-muted">{t.created_by_name}</span>
                      <SlaBadge slaDueAt={t.sla_due_at} breached={t.is_breached} />
                    </div>
                  </div>
                  <ManageControls ticket={t} onUpdated={loadAll} />
                  <MessageSquare size={14} className="text-muted shrink-0" />
                  {expanded === t.id ? <ChevronUp size={14} className="text-muted shrink-0" /> : <ChevronDown size={14} className="text-muted shrink-0" />}
                </div>
                {expanded === t.id && <CommentThread ticketId={t.id} />}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function TicketsPage() {
  return (
    <DashboardShell title="Tickets">
      <TicketsContent />
    </DashboardShell>
  );
}
