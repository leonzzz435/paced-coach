"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, CalendarDays, PlusCircle, MessageSquare,
  User, Trophy, Settings
} from "lucide-react";
import Image from "next/image";

import { computeCoachInboxBadgeCount, deriveCoachThreadSignals } from "@/lib/coach/inbox";
import type { CoachThreadsResponse } from "@/lib/types/coach";

type NavItem = {
  href: string;
  label: string;
  mobileLabel: string;
  exact: boolean;
  icon: typeof LayoutDashboard;
  showInMobileBottom?: boolean;
};

const NAV_ITEMS = [
  { href: "/app", label: "Dashboard", mobileLabel: "Home", exact: true, icon: LayoutDashboard, showInMobileBottom: true },
  { href: "/app/plan", label: "Training plan", mobileLabel: "Plan", exact: false, icon: CalendarDays, showInMobileBottom: true },
  { href: "/app/new", label: "Generate plans", mobileLabel: "Create", exact: false, icon: PlusCircle, showInMobileBottom: true },
  { href: "/app/competitions", label: "Competitions", mobileLabel: "Races", exact: false, icon: Trophy, showInMobileBottom: true },
  { href: "/app/coach", label: "Coach inbox", mobileLabel: "Coach", exact: false, icon: MessageSquare, showInMobileBottom: true },
  { href: "/app/profile", label: "Athlete profile", mobileLabel: "Profile", exact: false, icon: User, showInMobileBottom: true },
  { href: "/app/settings", label: "Settings", mobileLabel: "Settings", exact: false, icon: Settings, showInMobileBottom: false },
] satisfies NavItem[];

export default function AppNav({ variant }: { variant?: "desktop-rail" | "mobile-bottom" }) {
  const pathname = usePathname();
  const [coachBadgeCount, setCoachBadgeCount] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    let disposed = false;

    async function loadCoachBadge() {
      try {
        const listResponse = await fetch("/app/api/coach/threads?limit=30", { method: "GET", cache: "no-store" });
        if (!listResponse.ok) return;
        const threadsPayload = (await listResponse.json()) as CoachThreadsResponse;

        const activity = threadsPayload.items
          .filter((item) => item.messages)
          .map((item) => ({
            status: item.status,
            signals: deriveCoachThreadSignals({
              messages: item.messages ?? [],
              has_pending_proposal: item.has_pending_proposal ?? false,
              quota: { week_anchor_utc: "", used: 0, limit: 0, remaining: 0, is_limited: false },
              can_send_message: false,
              coach_gate_message: null,
              coach_gate_target: null,
              can_trigger_recap: false,
              training_provider_message: null,
              recap_gate_target: null,
              week_anchor_utc: "",
            }),
          }));

        const count = computeCoachInboxBadgeCount(activity);
        if (!disposed) {
          setCoachBadgeCount(count);
        }
      } catch {
        // Keep nav stable even if inbox summary cannot load.
      }
    }

    void loadCoachBadge();
    const timer = window.setInterval(() => void loadCoachBadge(), 60000);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, []);

  if (variant === "mobile-bottom") {
    const mobileItems = NAV_ITEMS.filter((item) => item.showInMobileBottom);
    return (
      <nav className="safe-bottom fixed bottom-0 z-40 w-full border-t border-[var(--border)] bg-[var(--surface)]/95 backdrop-blur pb-2 pt-1 lg:hidden">
        <div className="grid h-14 grid-cols-6 items-center px-1">
          {mobileItems.map((item) => {
            const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex flex-col items-center justify-center gap-1 rounded-lg px-1 py-1 text-[9px] font-medium transition-colors ${active ? "text-[var(--text-primary)]" : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                  }`}
              >
                <div className="relative">
                  <Icon className={`h-[18px] w-[18px] ${active ? "text-[var(--accent-primary)]" : "text-[var(--text-muted)]"}`} strokeWidth={active ? 2.5 : 2} />
                  {item.href === "/app/coach" && coachBadgeCount > 0 && (
                    <span className="absolute -right-2.5 -top-1.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-[var(--accent-danger)] px-1 text-[9px] font-bold text-white ring-2 ring-[var(--surface)]">
                      {coachBadgeCount > 99 ? "99+" : coachBadgeCount}
                    </span>
                  )}
                </div>
                <span className={`whitespace-nowrap ${active ? "font-semibold" : ""}`}>{item.mobileLabel}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    );
  }

  return (
    <aside
      className="group relative z-40 hidden h-full shrink-0 border-r border-[var(--border)] bg-[var(--surface)] transition-[width] duration-300 ease-in-out lg:flex lg:flex-col"
      style={{ width: isExpanded ? '260px' : '72px' }}
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => setIsExpanded(false)}
    >
      <div className="flex h-16 shrink-0 items-center px-4">
        <div className="flex items-center gap-3 overflow-hidden whitespace-nowrap">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-zinc-950 shadow-sm border border-[var(--border)]">
            <Image src="/favicon.svg" alt="Logo" width={32} height={32} className="rounded-xl object-contain" />
          </div>
          <div className={`flex flex-col transition-opacity duration-300 ${isExpanded ? 'opacity-100' : 'opacity-0'}`}>
            <span className="text-[10px] font-semibold tracking-[0.16em] text-[var(--text-muted)]">Agentic</span>
            <span className="text-sm font-bold tracking-tight text-[var(--text-primary)]">paced.coach</span>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1.5 overflow-y-auto overflow-x-hidden p-3 mt-4">
        {NAV_ITEMS.map((item) => {
          const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-xl py-2.5 transition-colors ${active
                ? "bg-[var(--accent-primary)] text-white shadow-sm"
                : "text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)] hover:text-[var(--text-primary)]"
                }`}
            >
              <div className="flex w-[48px] shrink-0 items-center justify-center">
                <div className="relative">
                  <Icon className={`h-[22px] w-[22px] ${active ? "text-white" : "text-[var(--text-muted)] group-hover:text-[var(--text-secondary)]"}`} strokeWidth={active ? 2.5 : 2} />
                  {item.href === "/app/coach" && coachBadgeCount > 0 && !isExpanded && (
                    <span className={`absolute -right-2 -top-1.5 flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold ring-2 ${active ? 'bg-[var(--accent-danger)] text-white ring-[var(--accent-primary)]' : 'bg-[var(--accent-danger)] text-white ring-[var(--surface)]'}`} />
                  )}
                </div>
              </div>
              <span className={`whitespace-nowrap text-sm font-medium transition-opacity duration-300 ${isExpanded ? 'opacity-100' : 'opacity-0'}`}>
                {item.label}
              </span>
              {item.href === "/app/coach" && coachBadgeCount > 0 && (
                <span
                  className={`border ml-auto mr-3 flex h-6 min-w-6 shrink-0 items-center justify-center rounded-full px-1.5 text-xs font-bold transition-opacity duration-300 ${isExpanded ? 'opacity-100' : 'opacity-0'} ${active ? 'bg-white/10 border-white/20 text-white' : 'bg-[var(--accent-danger)]/10 border-[var(--accent-danger)]/20 text-[var(--accent-danger)]'}`}
                >
                  {coachBadgeCount > 99 ? "99+" : coachBadgeCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[var(--border)] p-3 shrink-0 mb-2">
        <Link href="/app/settings" className="flex items-center gap-3 rounded-xl py-2 transition hover:bg-[var(--surface-elevated)]">
          <div className="flex w-[48px] shrink-0 items-center justify-center">
            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-emerald-400/20 bg-emerald-400/10">
              <Settings className="h-4 w-4 text-emerald-300" />
            </div>
          </div>
          <div className={`flex flex-col overflow-hidden whitespace-nowrap transition-opacity duration-300 ${isExpanded ? 'opacity-100' : 'opacity-0'}`}>
            <span className="text-sm font-semibold text-[var(--text-primary)]">Local app</span>
            <span className="text-xs font-medium text-[var(--text-muted)]">Setup and data</span>
          </div>
        </Link>
      </div>
    </aside>
  );
}
