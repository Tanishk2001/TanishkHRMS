"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutGrid,
  Sparkles,
  Users,
  CalendarClock,
  Megaphone,
  ScrollText,
  Ticket,
  Fingerprint,
  BarChart3,
  Laptop,
  DoorOpen,
  Heart,
  Clock,
  Activity,
} from "lucide-react";
import { getRole } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutGrid },
  { href: "/ai-copilot", label: "AI Copilot", icon: Sparkles, highlight: true },
  { href: "/employees", label: "Employees", icon: Users },
  { href: "/attendance", label: "Attendance", icon: Fingerprint },
  { href: "/leaves", label: "Leaves", icon: CalendarClock },
  { href: "/time-tracking", label: "Time Tracking", icon: Clock },
  { href: "/assets", label: "Assets", icon: Laptop },
  { href: "/exits", label: "Exits", icon: DoorOpen },
  { href: "/engagement", label: "Engagement", icon: Heart },
  { href: "/announcements", label: "Announcements", icon: Megaphone },
  { href: "/policies", label: "HR Policies", icon: ScrollText },
  { href: "/tickets", label: "Tickets", icon: Ticket },
  { href: "/reports", label: "Reports", icon: BarChart3, adminOnly: true },
  { href: "/ai-copilot/usage", label: "AI Usage", icon: Activity, adminOnly: true },
];

export default function Sidebar() {
  const pathname = usePathname();
  const role = typeof window !== "undefined" ? getRole() : null;
  const items = NAV.filter((item) => !item.adminOnly || role === "ADMIN");

  return (
    <aside className="w-60 shrink-0 bg-surface border-r border-border flex flex-col">
      <div className="h-16 flex items-center gap-2 px-5 border-b border-border">
        <div className="w-7 h-7 rounded-md bg-accent/20 flex items-center justify-center">
          <Sparkles size={16} className="text-accent" />
        </div>
        <span className="font-display font-bold tracking-tight text-[15px]">CB Nest</span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {items.map(({ href, label, icon: Icon, highlight }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`group flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-accent/15 text-ink"
                  : "text-muted hover:bg-surface-hi hover:text-ink"
              }`}
            >
              <Icon
                size={16}
                className={active ? "text-accent" : highlight ? "text-accent/70" : "text-muted group-hover:text-ink"}
              />
              <span>{label}</span>
              {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-accent" />}
            </Link>
          );
        })}
      </nav>

      <div className="px-5 py-4 border-t border-border">
        <p className="text-[11px] font-mono text-muted leading-relaxed">
          NovaWorks Technologies
          <br />
          PeopleOps Copilot v0.1
        </p>
      </div>
    </aside>
  );
}
