"use client";

import { useEffect, useState } from "react";
import { Laptop, PackageCheck, PackageX, Plus } from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import {
  listAssets, getMyAssets, createAsset, issueAsset, returnAsset,
  listEmployees, AssetWithHolder, EmployeeDirectoryRow, getRole,
} from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  AVAILABLE: "text-good",
  ASSIGNED: "text-accent",
  IN_REPAIR: "text-warn",
  RETIRED: "text-muted",
};

function AssetsContent() {
  const role = typeof window !== "undefined" ? getRole() : null;
  const canManage = role === "MANAGER" || role === "ADMIN";
  const canCreate = role === "ADMIN";

  const [assets, setAssets] = useState<AssetWithHolder[] | null>(null);
  const [employees, setEmployees] = useState<EmployeeDirectoryRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [issuingId, setIssuingId] = useState<number | null>(null);
  const [selectedEmployee, setSelectedEmployee] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);
  const [newTag, setNewTag] = useState("");
  const [newCategory, setNewCategory] = useState("LAPTOP");
  const [newName, setNewName] = useState("");

  function refresh() {
    const loader = canManage ? listAssets() : getMyAssets();
    loader.then(setAssets).catch((e) => setError(e.message));
    if (canManage) listEmployees().then(setEmployees).catch(() => {});
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleIssue(assetId: number) {
    if (!selectedEmployee) return;
    try {
      await issueAsset(assetId, Number(selectedEmployee));
      setIssuingId(null);
      setSelectedEmployee("");
      refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleReturn(assetId: number) {
    try {
      await returnAsset(assetId);
      refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createAsset({ asset_tag: newTag, category: newCategory, name: newName });
      setShowCreate(false);
      setNewTag("");
      setNewName("");
      refresh();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-4">
      {canCreate && (
        <div className="flex justify-end">
          <button
            onClick={() => setShowCreate((s) => !s)}
            className="flex items-center gap-1.5 text-xs font-medium bg-accent hover:bg-accent/90 transition-colors text-white rounded-lg px-3 py-2"
          >
            <Plus size={13} /> Add asset
          </button>
        </div>
      )}

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-surface border border-border rounded-xl p-4 flex gap-2 items-end">
          <div className="flex-1">
            <label className="block text-xs text-muted mb-1">Asset tag</label>
            <input value={newTag} onChange={(e) => setNewTag(e.target.value)} required
                   className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent" />
          </div>
          <div className="flex-1">
            <label className="block text-xs text-muted mb-1">Category</label>
            <select value={newCategory} onChange={(e) => setNewCategory(e.target.value)}
                    className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent">
              {["LAPTOP", "MONITOR", "MOBILE", "MOUSE", "SIM", "LICENSE", "ACCESSORY"].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-xs text-muted mb-1">Name</label>
            <input value={newName} onChange={(e) => setNewName(e.target.value)} required
                   className="w-full bg-base border border-border rounded-lg px-2.5 py-1.5 text-sm outline-none focus:border-accent" />
          </div>
          <button type="submit" className="bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium rounded-lg px-4 py-1.5">
            Save
          </button>
        </form>
      )}

      {error && <p className="text-sm text-bad">{error}</p>}
      {assets === null && !error && <p className="text-sm text-muted">Loading…</p>}
      {assets && assets.length === 0 && (
        <p className="text-sm text-muted">{canManage ? "No assets in inventory yet." : "No assets currently assigned to you."}</p>
      )}

      <div className="space-y-2">
        {assets?.map((a) => (
          <div key={a.id} className="bg-surface border border-border rounded-xl p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-accent/15 flex items-center justify-center shrink-0">
              <Laptop size={15} className="text-accent" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-ink truncate">{a.name}</p>
              <p className="text-[11px] text-muted font-mono">
                {a.asset_tag} · {a.category}
                {"current_holder_name" in a && a.current_holder_name && ` · ${a.current_holder_name}`}
              </p>
            </div>
            <span className={`text-xs font-mono font-medium ${STATUS_STYLES[a.status] ?? "text-muted"}`}>
              {a.status}
            </span>

            {canManage && a.status === "AVAILABLE" && issuingId !== a.id && (
              <button
                onClick={() => setIssuingId(a.id)}
                className="flex items-center gap-1 text-xs font-medium text-accent hover:underline"
              >
                <PackageCheck size={13} /> Issue
              </button>
            )}
            {canManage && a.status === "ASSIGNED" && (
              <button
                onClick={() => handleReturn(a.id)}
                className="flex items-center gap-1 text-xs font-medium text-muted hover:text-ink"
              >
                <PackageX size={13} /> Return
              </button>
            )}
            {canManage && issuingId === a.id && (
              <div className="flex items-center gap-1.5">
                <select
                  value={selectedEmployee}
                  onChange={(e) => setSelectedEmployee(e.target.value)}
                  className="bg-base border border-border rounded-md px-2 py-1 text-xs outline-none focus:border-accent"
                >
                  <option value="">Select employee…</option>
                  {employees?.map((emp) => (
                    <option key={emp.id} value={emp.id}>{emp.name}</option>
                  ))}
                </select>
                <button onClick={() => handleIssue(a.id)} className="text-xs font-medium text-accent hover:underline">
                  Confirm
                </button>
                <button onClick={() => setIssuingId(null)} className="text-xs text-muted hover:underline">
                  Cancel
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AssetsPage() {
  return (
    <DashboardShell title="Assets">
      <AssetsContent />
    </DashboardShell>
  );
}
