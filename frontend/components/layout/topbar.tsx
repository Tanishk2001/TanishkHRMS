"use client";

import { useEffect, useRef, useState } from "react";
import { Search, Bell, CalendarClock, Ticket as TicketIcon, DoorOpen } from "lucide-react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { clearToken, getRole, getTodayAttendance, listMyTickets, listExitRequests } from "@/lib/api";

interface Notification {
  id: string;
  icon: typeof CalendarClock;
  text: string;
  href: string;
}

export default function Topbar({ title }: { title: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const role = typeof window !== "undefined" ? getRole() : null;
  const currentQuery = searchParams.get("q") ?? "";

  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function loadNotifications() {
      const items: Notification[] = [];

      try {
        const today = await getTodayAttendance();
        if (!today.checked_in) {
          items.push({
            id: "no-checkin",
            icon: CalendarClock,
            text: "You haven't checked in today.",
            href: "/attendance",
          });
        }
      } catch {
        // not fatal — just skip this notification if the check fails
      }

      try {
        const tickets = await listMyTickets();
        const openCount = tickets.filter((t) => t.status !== "CLOSED").length;
        if (openCount > 0) {
          items.push({
            id: "open-tickets",
            icon: TicketIcon,
            text: `You have ${openCount} open ticket${openCount === 1 ? "" : "s"}.`,
            href: "/tickets",
          });
        }
      } catch {
        // ignore
      }

      if (role === "MANAGER" || role === "ADMIN") {
        try {
          const exits = await listExitRequests();
          const pendingCount = exits.filter((e) => e.status === "PENDING").length;
          if (pendingCount > 0) {
            items.push({
              id: "pending-exits",
              icon: DoorOpen,
              text: `${pendingCount} exit request${pendingCount === 1 ? "" : "s"} awaiting your decision.`,
              href: "/exits",
            });
          }
        } catch {
          // ignore
        }
      }

      setNotifications(items);
    }
    loadNotifications();
  }, [role]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const SEARCHABLE_PATHS = ["/employees", "/policies"];

  function handleSearchChange(value: string) {
    const navigatingToNewPage = !SEARCHABLE_PATHS.includes(pathname);
    const targetPath = navigatingToNewPage ? "/employees" : pathname;
    const params = new URLSearchParams(navigatingToNewPage ? "" : searchParams.toString());
    if (value) {
      params.set("q", value);
    } else {
      params.delete("q");
    }
    const url = `${targetPath}?${params.toString()}`;
    if (navigatingToNewPage) {
      router.push(url);
    } else {
      router.replace(url);
    }
  }

  return (
    <header className="relative z-30 h-16 shrink-0 border-b border-border bg-surface/60 backdrop-blur flex items-center justify-between px-6">
      <div>
        <p className="text-[11px] uppercase tracking-widest text-muted font-mono">Workspace</p>
        <h1 className="font-display font-bold text-lg leading-none -mt-0.5">{title}</h1>
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden sm:flex items-center gap-2 bg-base border border-border rounded-lg px-3 py-1.5 w-72">
          <Search size={14} className="text-muted" />
          <input
            value={currentQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search employees, policies..."
            className="bg-transparent text-sm outline-none placeholder:text-muted w-full"
          />
        </div>

        <div className="relative" ref={panelRef}>
          <button
            onClick={() => setOpen((o) => !o)}
            className="relative w-9 h-9 rounded-lg border border-border flex items-center justify-center text-muted hover:text-ink hover:bg-surface-hi transition-colors"
          >
            <Bell size={16} />
            {notifications.length > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-accent text-white text-[10px] flex items-center justify-center font-mono">
                {notifications.length}
              </span>
            )}
          </button>

          {open && (
            <div className="absolute right-0 mt-2 w-72 bg-surface border border-border rounded-xl shadow-glow overflow-hidden z-10">
              <div className="px-3 py-2 border-b border-border">
                <p className="text-[11px] uppercase tracking-widest text-muted font-mono">Notifications</p>
              </div>
              {notifications.length === 0 ? (
                <p className="text-sm text-muted px-3 py-4 text-center">You&rsquo;re all caught up.</p>
              ) : (
                <div>
                  {notifications.map((n) => (
                    <button
                      key={n.id}
                      onClick={() => {
                        setOpen(false);
                        router.push(n.href);
                      }}
                      className="w-full flex items-start gap-2.5 px-3 py-2.5 text-left hover:bg-surface-hi transition-colors border-b border-border last:border-b-0"
                    >
                      <n.icon size={14} className="text-accent shrink-0 mt-0.5" />
                      <span className="text-sm text-ink">{n.text}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <button
          onClick={() => {
            clearToken();
            router.push("/");
          }}
          className="flex items-center gap-2 pl-3 pr-1 py-1 rounded-full border border-border hover:bg-surface-hi transition-colors"
        >
          <span className="text-xs text-muted font-mono">{role ?? "—"}</span>
          <span className="w-7 h-7 rounded-full bg-accent/25 text-accent flex items-center justify-center text-xs font-semibold">
            {role ? role[0] : "?"}
          </span>
        </button>
      </div>
    </header>
  );
}
