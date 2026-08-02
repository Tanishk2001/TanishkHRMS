"use client";

import { useEffect, useState, ReactNode, Suspense } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/api";
import Sidebar from "./sidebar";
import Topbar from "./topbar";

export default function DashboardShell({ title, children }: { title: string; children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.push("/");
      return;
    }
    setReady(true);
  }, [router]);

  if (!ready) return null;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Suspense fallback={<div className="h-16 shrink-0 border-b border-border" />}>
          <Topbar title={title} />
        </Suspense>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
