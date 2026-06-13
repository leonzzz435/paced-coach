"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { ChevronRight, Settings, User, X } from "lucide-react";

type MenuItem = {
  href: string;
  label: string;
  description: string;
  icon: typeof User;
  exact?: boolean;
};

const MENU_ITEMS: MenuItem[] = [
  {
    href: "/app/profile",
    label: "Athlete profile",
    description: "Edit physiology, constraints, and goals.",
    icon: User,
  },
  {
    href: "/app/settings",
    label: "Setup & data",
    description: "Manage integrations, sync controls, and local reset.",
    icon: Settings,
  },
];

export default function MobileAccountMenu() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const originalOverflow = document.body.style.overflow;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [isOpen]);

  return (
    <>
      <button
        type="button"
        aria-expanded={isOpen}
        aria-controls="mobile-account-menu"
        aria-haspopup="dialog"
        className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-[var(--surface)] shadow-sm transition hover:border-white/20 hover:bg-white/[0.04]"
        onClick={() => setIsOpen(true)}
      >
        <User className="h-5 w-5 text-[var(--accent-primary)]" strokeWidth={2.25} />
        <span className="sr-only">Open account menu</span>
      </button>

      {isOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Close account menu"
            className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm"
            onClick={() => setIsOpen(false)}
          />

          <div
            id="mobile-account-menu"
            role="dialog"
            aria-modal="true"
            aria-label="Account menu"
            className="safe-bottom absolute inset-x-0 bottom-0 rounded-t-[2rem] border border-[var(--border)] bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.16),transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] px-4 pb-4 pt-3 shadow-[0_-24px_64px_rgba(2,6,23,0.48)]"
          >
            <div className="mx-auto h-1.5 w-12 rounded-full bg-white/12" />

            <div className="mt-4 flex items-start justify-between gap-3">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">Local app</div>
                <h2 className="mt-2 text-xl font-semibold tracking-tight text-[var(--text-primary)]">Manage your setup</h2>
                <p className="mt-2 max-w-sm text-sm leading-6 text-[var(--text-secondary)]">
                  Reach local profile and setup controls without adding another bottom tab.
                </p>
              </div>

              <button
                type="button"
                aria-label="Close account menu"
                className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-[var(--surface)] transition hover:border-white/20 hover:bg-white/[0.04]"
                onClick={() => setIsOpen(false)}
              >
                <X className="h-4 w-4 text-[var(--text-secondary)]" />
              </button>
            </div>

            <div className="mt-5 space-y-2">
              {MENU_ITEMS.map((item) => {
                const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
                const Icon = item.icon;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 rounded-[1.4rem] border px-4 py-3 transition ${active
                      ? "border-sky-400/30 bg-sky-400/10"
                      : "border-white/8 bg-[var(--surface)]/88 hover:border-white/14 hover:bg-white/[0.04]"
                      }`}
                    onClick={() => setIsOpen(false)}
                  >
                    <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${active ? "bg-sky-400/14" : "bg-white/[0.04]"}`}>
                      <Icon className={`h-5 w-5 ${active ? "text-sky-300" : "text-[var(--text-secondary)]"}`} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-semibold text-[var(--text-primary)]">{item.label}</div>
                      <p className="mt-1 text-xs leading-5 text-[var(--text-secondary)]">{item.description}</p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-[var(--text-muted)]" />
                  </Link>
                );
              })}
            </div>

            <div className="mt-4 rounded-[1.4rem] border border-emerald-400/15 bg-emerald-400/[0.08] px-4 py-3 text-xs leading-5 text-emerald-100/80">
              Single-user local mode is active by default. There is no hosted account or sign-out flow in OSS v1.
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
