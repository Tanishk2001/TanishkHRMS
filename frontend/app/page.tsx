"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { login, setToken, setRole } from "@/lib/api";

const SEED_ACCOUNTS = [
  { label: "Admin", email: "admin@novaworks.com", password: "admin123" },
  { label: "Manager", email: "rahul.manager@novaworks.com", password: "manager123" },
  { label: "Employee", email: "employee@novaworks.com", password: "employee123" },
];

export default function LoginPage() {
  const router = useRouter();
  const isDev = process.env.NODE_ENV !== "production";
  const [email, setEmail] = useState(isDev ? "employee@novaworks.com" : "");
  const [password, setPassword] = useState(isDev ? "employee123" : "");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await login(email, password);
      setToken(res.access_token);
      setRole(res.role);
      router.push("/dashboard");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-4 bg-base relative overflow-hidden">
      <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full bg-accent/10 blur-[120px]" />

      <form
        onSubmit={handleSubmit}
        className="relative w-full max-w-sm bg-surface border border-border rounded-2xl p-7 shadow-glow"
      >
        <div className="flex items-center gap-2 mb-1">
          <div className="w-7 h-7 rounded-md bg-accent/20 flex items-center justify-center">
            <Sparkles size={15} className="text-accent" />
          </div>
          <h1 className="font-display font-bold text-lg">CB Nest</h1>
        </div>
        <p className="text-sm text-muted mb-6">Sign in to reach the PeopleOps Copilot.</p>

        <label className="block text-xs font-medium text-muted mb-1.5">Email</label>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full mb-4 rounded-lg border border-border bg-base px-3 py-2.5 text-sm outline-none focus:border-accent transition-colors"
        />

        <label className="block text-xs font-medium text-muted mb-1.5">Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full mb-5 rounded-lg border border-border bg-base px-3 py-2.5 text-sm outline-none focus:border-accent transition-colors"
        />

        {error && <p className="text-sm text-bad mb-4">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-accent hover:bg-accent/90 transition-colors text-white text-sm font-medium py-2.5 disabled:opacity-50"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>

        {isDev && (
          <div className="mt-6 pt-5 border-t border-border space-y-1.5">
            <p className="text-[11px] uppercase tracking-widest text-muted font-mono mb-2">
              Seed accounts (dev only)
            </p>
            {SEED_ACCOUNTS.map((acc) => (
              <button
                key={acc.email}
                type="button"
                onClick={() => {
                  setEmail(acc.email);
                  setPassword(acc.password);
                }}
                className="w-full flex items-center justify-between text-xs px-2.5 py-1.5 rounded-md hover:bg-surface-hi transition-colors text-left"
              >
                <span className="text-ink">{acc.label}</span>
                <span className="text-muted font-mono">{acc.email}</span>
              </button>
            ))}
          </div>
        )}
      </form>
    </main>
  );
}
