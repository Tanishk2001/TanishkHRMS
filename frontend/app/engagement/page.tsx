"use client";

import { useEffect, useState } from "react";
import { Vote, Heart, Plus, X, Lock } from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import {
  listPolls, createPoll, voteInPoll, closePoll,
  listKudos, giveKudos, listEmployees,
  PollRow, KudosRow, EmployeeDirectoryRow, getRole,
} from "@/lib/api";

const CATEGORIES = ["TEAMWORK", "INNOVATION", "LEADERSHIP", "CUSTOMER_FOCUS", "OTHER"];

function PollCard({ poll, canManage, onChanged }: { poll: PollRow; canManage: boolean; onChanged: () => void }) {
  const [error, setError] = useState<string | null>(null);
  const hasVoted = poll.my_vote_option_id !== null;
  const isClosed = poll.status === "CLOSED";

  async function handleVote(optionId: number) {
    try {
      await voteInPoll(poll.id, optionId);
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleClose() {
    try {
      await closePoll(poll.id);
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Vote size={14} className="text-accent" />
          <p className="text-sm text-ink font-medium">{poll.question}</p>
        </div>
        <span className={`text-xs font-mono ${isClosed ? "text-muted" : "text-good"}`}>{poll.status}</span>
      </div>

      <div className="space-y-2">
        {poll.options.map((opt) => {
          const pct = poll.total_votes > 0 ? Math.round((opt.vote_count / poll.total_votes) * 100) : 0;
          const isMine = poll.my_vote_option_id === opt.id;
          return (
            <button
              key={opt.id}
              onClick={() => !hasVoted && !isClosed && handleVote(opt.id)}
              disabled={hasVoted || isClosed}
              className={`w-full text-left relative overflow-hidden rounded-lg border ${
                isMine ? "border-accent" : "border-border"
              } ${!hasVoted && !isClosed ? "hover:border-accent/60 cursor-pointer" : "cursor-default"}`}
            >
              {(hasVoted || isClosed) && (
                <div className="absolute inset-y-0 left-0 bg-accent/15" style={{ width: `${pct}%` }} />
              )}
              <div className="relative flex items-center justify-between px-3 py-2 text-sm">
                <span className="text-ink">{opt.option_text}</span>
                {(hasVoted || isClosed) && (
                  <span className="text-xs font-mono text-muted">{pct}% ({opt.vote_count})</span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {error && <p className="text-xs text-bad mt-2">{error}</p>}

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
        <span className="text-[11px] text-muted font-mono">
          {poll.total_votes} vote{poll.total_votes === 1 ? "" : "s"} · by {poll.created_by_name}
        </span>
        {canManage && !isClosed && (
          <button onClick={handleClose} className="flex items-center gap-1 text-xs text-muted hover:text-ink">
            <Lock size={11} /> Close poll
          </button>
        )}
      </div>
    </div>
  );
}

function EngagementContent() {
  const role = typeof window !== "undefined" ? getRole() : null;
  const canManagePolls = role === "MANAGER" || role === "ADMIN";

  const [polls, setPolls] = useState<PollRow[] | null>(null);
  const [kudos, setKudos] = useState<KudosRow[] | null>(null);
  const [employees, setEmployees] = useState<EmployeeDirectoryRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [showPollForm, setShowPollForm] = useState(false);
  const [question, setQuestion] = useState("");
  const [options, setOptions] = useState(["", ""]);

  const [showKudosForm, setShowKudosForm] = useState(false);
  const [kudosTo, setKudosTo] = useState("");
  const [kudosCategory, setKudosCategory] = useState("TEAMWORK");
  const [kudosMessage, setKudosMessage] = useState("");

  function refresh() {
    listPolls().then(setPolls).catch((e) => setError(e.message));
    listKudos().then(setKudos).catch(() => {});
    listEmployees().then(setEmployees).catch(() => {});
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreatePoll(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createPoll(question, options.filter((o) => o.trim()));
      setShowPollForm(false);
      setQuestion("");
      setOptions(["", ""]);
      refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleGiveKudos(e: React.FormEvent) {
    e.preventDefault();
    if (!kudosTo) return;
    try {
      await giveKudos(Number(kudosTo), kudosCategory, kudosMessage);
      setShowKudosForm(false);
      setKudosTo("");
      setKudosMessage("");
      refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-8">
      {error && <p className="text-sm text-bad">{error}</p>}

      {/* Polls */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-semibold text-[15px] flex items-center gap-2">
            <Vote size={16} className="text-accent" /> Polls
          </h2>
          {canManagePolls && (
            <button
              onClick={() => setShowPollForm((s) => !s)}
              className="flex items-center gap-1 text-xs font-medium text-accent hover:underline"
            >
              <Plus size={13} /> New poll
            </button>
          )}
        </div>

        {showPollForm && (
          <form onSubmit={handleCreatePoll} className="bg-surface border border-border rounded-xl p-4 space-y-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Poll question"
              required
              className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent"
            />
            {options.map((opt, i) => (
              <div key={i} className="flex gap-2">
                <input
                  value={opt}
                  onChange={(e) => setOptions((prev) => prev.map((o, idx) => (idx === i ? e.target.value : o)))}
                  placeholder={`Option ${i + 1}`}
                  required={i < 2}
                  className="flex-1 bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent"
                />
                {options.length > 2 && (
                  <button type="button" onClick={() => setOptions((prev) => prev.filter((_, idx) => idx !== i))}>
                    <X size={14} className="text-muted hover:text-bad" />
                  </button>
                )}
              </div>
            ))}
            <div className="flex justify-between items-center pt-1">
              <button type="button" onClick={() => setOptions((prev) => [...prev, ""])} className="text-xs text-accent hover:underline">
                + Add option
              </button>
              <button type="submit" className="bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium rounded-lg px-4 py-1.5">
                Create poll
              </button>
            </div>
          </form>
        )}

        {polls === null && <p className="text-sm text-muted">Loading…</p>}
        {polls?.map((p) => (
          <PollCard key={p.id} poll={p} canManage={canManagePolls} onChanged={refresh} />
        ))}
      </section>

      {/* Kudos */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-semibold text-[15px] flex items-center gap-2">
            <Heart size={16} className="text-accent" /> Kudos
          </h2>
          <button
            onClick={() => setShowKudosForm((s) => !s)}
            className="flex items-center gap-1 text-xs font-medium text-accent hover:underline"
          >
            <Plus size={13} /> Give kudos
          </button>
        </div>

        {showKudosForm && (
          <form onSubmit={handleGiveKudos} className="bg-surface border border-border rounded-xl p-4 space-y-2">
            <select
              value={kudosTo}
              onChange={(e) => setKudosTo(e.target.value)}
              required
              className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent"
            >
              <option value="">Give kudos to…</option>
              {employees?.map((emp) => (
                <option key={emp.id} value={emp.id}>{emp.name}</option>
              ))}
            </select>
            <select
              value={kudosCategory}
              onChange={(e) => setKudosCategory(e.target.value)}
              className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c.replace("_", " ")}</option>
              ))}
            </select>
            <textarea
              value={kudosMessage}
              onChange={(e) => setKudosMessage(e.target.value)}
              placeholder="What did they do well?"
              required
              rows={2}
              className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent resize-none"
            />
            <div className="flex justify-end">
              <button type="submit" className="bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium rounded-lg px-4 py-1.5">
                Send kudos
              </button>
            </div>
          </form>
        )}

        {kudos === null && <p className="text-sm text-muted">Loading…</p>}
        {kudos?.length === 0 && <p className="text-sm text-muted">No kudos yet — be the first!</p>}
        <div className="space-y-2">
          {kudos?.map((k) => (
            <div key={k.id} className="bg-surface border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm text-ink font-medium">{k.from_employee_name}</span>
                <span className="text-xs text-muted">→</span>
                <span className="text-sm text-ink font-medium">{k.to_employee_name}</span>
                <span className="ml-auto text-[10px] uppercase tracking-widest text-accent font-mono">
                  {k.category.replace("_", " ")}
                </span>
              </div>
              <p className="text-sm text-muted">{k.message}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export default function EngagementPage() {
  return (
    <DashboardShell title="Engagement">
      <EngagementContent />
    </DashboardShell>
  );
}
