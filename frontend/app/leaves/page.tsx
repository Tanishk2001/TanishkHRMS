"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CalendarClock, ArrowRight } from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import { getLeaveBalance, LeaveBalanceRow } from "@/lib/api";

function LeavesContent() {
  const router = useRouter();
  const [balances, setBalances] = useState<LeaveBalanceRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getLeaveBalance()
      .then(setBalances)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-5">
      <div className="bg-surface border border-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <CalendarClock size={16} className="text-accent" />
          <h2 className="font-display font-semibold text-[15px]">Your leave balance</h2>
        </div>

        {error && <p className="text-sm text-bad">{error}</p>}
        {balances === null && !error && <p className="text-sm text-muted">Loading…</p>}
        {balances && (
          <div className="grid grid-cols-3 gap-3">
            {balances.map((b) => (
              <div key={b.leave_type} className="bg-base border border-border rounded-lg p-4 text-center">
                <p className="text-2xl font-mono font-semibold text-ink">{b.balance_days}</p>
                <p className="text-xs text-muted mt-1">{b.leave_type}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={() => router.push("/ai-copilot?tab=action")}
        className="w-full flex items-center justify-center gap-2 bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium rounded-lg py-3"
      >
        Apply for leave via the Copilot <ArrowRight size={14} />
      </button>
      <p className="text-xs text-muted text-center">
        e.g. &ldquo;Apply casual leave for tomorrow because of personal work.&rdquo;
      </p>
    </div>
  );
}

export default function LeavesPage() {
  return (
    <DashboardShell title="Leaves">
      <LeavesContent />
    </DashboardShell>
  );
}
