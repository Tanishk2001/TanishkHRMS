"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import DashboardShell from "@/components/layout/shell";
import ChatPanel from "@/components/ai/chat-panel";

type Mode = "policy" | "sql" | "action" | "recent";
const VALID_MODES: Mode[] = ["policy", "sql", "action", "recent"];

function AICopilotContent() {
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const initialMode: Mode = VALID_MODES.includes(tabParam as Mode) ? (tabParam as Mode) : "policy";
  const initialMessage = searchParams.get("q") ?? undefined;

  return (
    <div className="h-full max-w-3xl mx-auto bg-surface border-x border-border">
      <ChatPanel initialMode={initialMode} initialMessage={initialMessage} />
    </div>
  );
}

export default function AICopilotPage() {
  return (
    <DashboardShell title="AI Copilot">
      <Suspense fallback={null}>
        <AICopilotContent />
      </Suspense>
    </DashboardShell>
  );
}
