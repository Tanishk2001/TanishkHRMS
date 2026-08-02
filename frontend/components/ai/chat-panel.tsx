"use client";

import { useState, useEffect, useRef } from "react";
import { askPolicy, askSql, askAction, getRole, PolicySource } from "@/lib/api";
import SourceList from "./source-list";
import SqlResultTable from "./sql-result-table";
import ActionResultCard from "./action-result-card";
import RecentActionsPanel from "./recent-actions-panel";

type Mode = "policy" | "sql" | "action" | "recent";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  mode: Mode;
  content: string;
  sources?: PolicySource[];
  rows?: Record<string, unknown>[];
  sql?: string | null;
  status?: string;
  needsConfirmation?: boolean;
  pendingAction?: Record<string, unknown> | null;
  isError?: boolean;
}

const MODE_LABELS: Record<Mode, string> = {
  policy: "Ask HR Policy",
  sql: "Ask About People & Projects",
  action: "Automate HR Task",
  recent: "Recent AI Actions",
};

const MODE_PLACEHOLDERS: Record<Mode, string> = {
  policy: "e.g. How many sick leaves do I get?",
  sql: "e.g. Which employees know Python?",
  action: "e.g. Apply casual leave for tomorrow because of personal work.",
  recent: "",
};

// Role-specific copilot mode label shown above the tab strip — the
// underlying tabs/permissions are already role-gated server-side
// (services/ai/permissions.py); this just makes that visible in the UI.
const COPILOT_TITLE_BY_ROLE: Record<string, string> = {
  EMPLOYEE: "Employee Copilot",
  MANAGER: "Manager Copilot",
  ADMIN: "Admin Copilot",
};

function newId() {
  return Math.random().toString(36).slice(2);
}

export default function ChatPanel({
  initialMode = "policy",
  initialMessage,
}: {
  initialMode?: Mode;
  initialMessage?: string;
}) {
  const [mode, setMode] = useState<Mode>(initialMode);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const firedInitial = useRef(false);

  useEffect(() => {
    if (initialMessage && !firedInitial.current) {
      firedInitial.current = true;
      send(initialMessage);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function send(overrideText?: string, confirm = false, pendingAction: Record<string, unknown> | null = null) {
    if (mode === "recent") return;
    const text = overrideText ?? input;
    if (!text.trim() || loading) return;

    if (!confirm) {
      setMessages((m) => [...m, { id: newId(), role: "user", mode, content: text }]);
      setInput("");
    }
    setLoading(true);

    try {
      if (mode === "policy") {
        const res = await askPolicy(text);
        if (!res.success || !res.data) throw new Error(res.error || "No answer available.");
        setMessages((m) => [
          ...m,
          { id: newId(), role: "assistant", mode, content: res.data!.answer, sources: res.data!.sources },
        ]);
      } else if (mode === "sql") {
        const res = await askSql(text);
        if (!res.success || !res.data) throw new Error(res.error || "That request couldn't be run.");
        setMessages((m) => [
          ...m,
          { id: newId(), role: "assistant", mode, content: res.data!.answer, rows: res.data!.rows, sql: res.data!.sql },
        ]);
      } else {
        const res = await askAction(text, confirm, pendingAction);
        const data = res.data;
        if (!data) throw new Error(res.error || "Action failed.");
        setMessages((m) => [
          ...m,
          {
            id: newId(),
            role: "assistant",
            mode,
            content: data.answer,
            status: data.status,
            needsConfirmation: data.needs_confirmation,
            pendingAction: data.pending_action,
          },
        ]);
      }
    } catch (err) {
      setMessages((m) => [
        ...m,
        { id: newId(), role: "assistant", mode, content: (err as Error).message, isError: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const role = getRole();
  const copilotTitle = (role && COPILOT_TITLE_BY_ROLE[role]) || "AI Copilot";

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-4 text-[11px] uppercase tracking-widest text-muted font-mono">
        {copilotTitle}
      </div>
      <div className="flex gap-1 border-b border-border px-4 pt-1">
        {(Object.keys(MODE_LABELS) as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-3 py-2 text-sm rounded-t-md border-b-2 transition-colors ${
              mode === m
                ? "border-accent text-ink font-medium"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {MODE_LABELS[m]}
          </button>
        ))}
      </div>

      {mode === "recent" ? (
        <RecentActionsPanel />
      ) : (
      <>
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-sm text-muted">{MODE_PLACEHOLDERS[mode]}</p>
        )}
        {messages.map((msg) => (
          <div key={msg.id} className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                msg.role === "user"
                  ? "bg-accent text-white"
                  : msg.isError
                  ? "bg-bad/10 text-bad border border-bad/30"
                  : "bg-surface-hi text-ink border border-border"
              }`}
            >
              {msg.mode === "action" && msg.role === "assistant" && msg.status ? (
                <ActionResultCard
                  answer={msg.content}
                  status={msg.status}
                  needsConfirmation={!!msg.needsConfirmation}
                  onConfirm={() => send(msg.content, true, msg.pendingAction ?? null)}
                  onCancel={() =>
                    setMessages((m) => [
                      ...m,
                      { id: newId(), role: "assistant", mode: "action", content: "Cancelled." },
                    ])
                  }
                />
              ) : (
                <>
                  <p>{msg.content}</p>
                  {msg.sources && <SourceList sources={msg.sources} />}
                  {msg.rows && <SqlResultTable rows={msg.rows} sql={msg.sql ?? null} />}
                </>
              )}
            </div>
          </div>
        ))}
        {loading && <p className="text-sm text-muted">Thinking…</p>}
      </div>

      <div className="border-t border-border p-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={MODE_PLACEHOLDERS[mode]}
          className="flex-1 rounded-lg border border-border bg-base px-3 py-2 text-sm outline-none focus:border-accent transition-colors"
        />
        <button
          onClick={() => send()}
          disabled={loading}
          className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium disabled:opacity-50"
        >
          Send
        </button>
      </div>
      </>
      )}
    </div>
  );
}
