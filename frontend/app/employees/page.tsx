"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { UserPlus } from "lucide-react";
import DashboardShell from "@/components/layout/shell";
import {
  listEmployees, listDepartments, createEmployee, getRole,
  EmployeeDirectoryRow, DepartmentRow,
} from "@/lib/api";

function AddEmployeeForm({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [departments, setDepartments] = useState<DepartmentRow[] | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("EMPLOYEE");
  const [jobTitle, setJobTitle] = useState("");
  const [departmentId, setDepartmentId] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && departments === null) {
      listDepartments().then(setDepartments).catch(() => setDepartments([]));
    }
  }, [open, departments]);

  async function submit() {
    if (!name.trim() || !email.trim() || password.length < 6) {
      setError("Name, email, and a password of at least 6 characters are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createEmployee({
        name: name.trim(),
        email: email.trim(),
        password,
        role,
        job_title: jobTitle.trim() || null,
        department_id: departmentId ? Number(departmentId) : null,
      });
      setName(""); setEmail(""); setPassword(""); setRole("EMPLOYEE"); setJobTitle(""); setDepartmentId("");
      setOpen(false);
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add employee");
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium rounded-lg px-4 py-2 mb-4"
      >
        <UserPlus size={14} /> Add Employee
      </button>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-4 space-y-3 mb-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Full name"
          className="bg-base border border-border rounded-lg px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:border-accent"
        />
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Work email"
          type="email"
          className="bg-base border border-border rounded-lg px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:border-accent"
        />
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Temporary password"
          type="password"
          className="bg-base border border-border rounded-lg px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:border-accent"
        />
        <input
          value={jobTitle}
          onChange={(e) => setJobTitle(e.target.value)}
          placeholder="Job title (optional)"
          className="bg-base border border-border rounded-lg px-3 py-2 text-sm text-ink placeholder:text-muted focus:outline-none focus:border-accent"
        />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="bg-base border border-border rounded-lg px-3 py-2 text-sm text-ink focus:outline-none focus:border-accent"
        >
          {["EMPLOYEE", "MANAGER", "ADMIN"].map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <select
          value={departmentId}
          onChange={(e) => setDepartmentId(e.target.value)}
          className="bg-base border border-border rounded-lg px-3 py-2 text-sm text-ink focus:outline-none focus:border-accent"
        >
          <option value="">No department</option>
          {departments?.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </div>
      <div className="flex items-center justify-end gap-2">
        <button onClick={() => setOpen(false)} className="text-xs text-muted px-3 py-1.5">Cancel</button>
        <button
          onClick={submit}
          disabled={submitting}
          className="bg-accent hover:bg-accent/90 disabled:opacity-50 transition-colors text-white text-xs font-medium rounded-lg px-4 py-1.5"
        >
          {submitting ? "Adding…" : "Add employee"}
        </button>
      </div>
      {error && <p className="text-xs text-bad">{error}</p>}
    </div>
  );
}

function EmployeesContent() {
  const searchParams = useSearchParams();
  const query = (searchParams.get("q") ?? "").toLowerCase().trim();
  const role = typeof window !== "undefined" ? getRole() : null;

  const [rows, setRows] = useState<EmployeeDirectoryRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    listEmployees()
      .then(setRows)
      .catch((e) => setError(e.message));
  }

  useEffect(load, []);

  const filtered = rows?.filter((r) => {
    if (!query) return true;
    return (
      r.name.toLowerCase().includes(query) ||
      (r.job_title ?? "").toLowerCase().includes(query) ||
      (r.department ?? "").toLowerCase().includes(query) ||
      r.role.toLowerCase().includes(query)
    );
  });

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <p className="text-sm text-muted mb-4">
        Directory listing — name, title, and department only. Salary, bank, and PAN details are never exposed here or via the AI copilot.
      </p>
      {role === "ADMIN" && <AddEmployeeForm onCreated={load} />}
      {error && <p className="text-sm text-bad">{error}</p>}
      {rows === null && !error && <p className="text-sm text-muted">Loading…</p>}
      {filtered && filtered.length === 0 && (
        <p className="text-sm text-muted">No employees match &ldquo;{query}&rdquo;.</p>
      )}
      {filtered && filtered.length > 0 && (
        <div className="overflow-x-auto border border-border rounded-xl bg-surface">
          <table className="min-w-full text-sm">
            <thead className="bg-base">
              <tr>
                <th className="text-left font-medium text-muted px-4 py-2.5 font-mono text-xs">Name</th>
                <th className="text-left font-medium text-muted px-4 py-2.5 font-mono text-xs">Title</th>
                <th className="text-left font-medium text-muted px-4 py-2.5 font-mono text-xs">Department</th>
                <th className="text-left font-medium text-muted px-4 py-2.5 font-mono text-xs">Role</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.id} className="border-t border-border">
                  <td className="px-4 py-2.5 text-ink">{r.name}</td>
                  <td className="px-4 py-2.5 text-muted">{r.job_title ?? "—"}</td>
                  <td className="px-4 py-2.5 text-muted">{r.department ?? "—"}</td>
                  <td className="px-4 py-2.5 text-muted font-mono text-xs">{r.role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function EmployeesPage() {
  return (
    <DashboardShell title="Employees">
      <Suspense fallback={null}>
        <EmployeesContent />
      </Suspense>
    </DashboardShell>
  );
}
