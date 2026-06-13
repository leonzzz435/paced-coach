"use client";

import { useState } from "react";

import Sparkline from "@/components/dashboard/sparkline";
import type { UiKpi, UiKpiStatus } from "@/lib/types/ui-blocks";

type StatusSurface = {
  kpis: UiKpi[];
  source: "daily_update" | "analysis" | "none";
  label: string | null;
  updated_at: string | null;
  target_date: string | null;
};

type Props = {
  surface: StatusSurface;
};

function statusColor(status: UiKpiStatus): { dot: string; stroke: string; ring: string; badge: string; glow: string } {
  switch (status) {
    case "good":
      return { dot: "bg-emerald-500", stroke: "#22c55e", ring: "ring-emerald-500/20", badge: "text-emerald-400", glow: "shadow-[var(--glow-success)]" };
    case "warning":
      return { dot: "bg-amber-500", stroke: "#f59e0b", ring: "ring-amber-500/20", badge: "text-amber-400", glow: "shadow-[var(--glow-warning)]" };
    case "danger":
      return { dot: "bg-rose-500", stroke: "#ef4444", ring: "ring-rose-500/20", badge: "text-rose-400", glow: "shadow-[var(--glow-danger)]" };
    default:
      return { dot: "bg-zinc-500", stroke: "#71717a", ring: "ring-zinc-500/20", badge: "text-[var(--text-muted)]", glow: "" };
  }
}

function sourceLabel(source: StatusSurface["source"]): string | null {
  if (source === "daily_update") return "Morning sync";
  if (source === "analysis") return "Baseline analysis";
  return null;
}

export default function StatusGauges({ surface }: Props) {
  const [openKpiId, setOpenKpiId] = useState<string | null>(null);

  if (!surface.kpis.length) return null;

  const source = surface.label ?? sourceLabel(surface.source);

  return (
    <div className="flex w-full flex-col gap-2">
      {source ? (
        <div className="flex items-center gap-2 px-1 text-[11px] font-semibold text-[var(--text-muted)]">
          <span>{source}</span>
          {surface.updated_at ? <span className="text-[var(--text-dim)]">{new Date(surface.updated_at).toLocaleString()}</span> : null}
        </div>
      ) : null}

      <div className="flex w-full flex-wrap items-center gap-x-4 gap-y-2 pb-2 lg:pb-0">
        {surface.kpis.map((kpi) => {
          const colors = statusColor(kpi.status);
          const showSpark = Array.isArray(kpi.trend_points) && kpi.trend_points.length >= 2;
          const isOpen = openKpiId === kpi.kpi_id;

          return (
            <div
              key={kpi.kpi_id}
              className="relative shrink-0"
              onMouseEnter={() => setOpenKpiId(kpi.kpi_id)}
              onMouseLeave={() => setOpenKpiId(null)}
              onClick={() => setOpenKpiId(isOpen ? null : kpi.kpi_id)}
            >
              <div className="flex cursor-pointer items-center gap-2 rounded-xl bg-[var(--surface)] border border-[var(--border)] px-3 py-2 transition-colors hover:bg-[var(--surface-elevated)]">
                <span className={`h-2.5 w-2.5 shrink-0 rounded-full ring-2 ${colors.dot} ${colors.ring} ${colors.glow}`} />
                <span className="whitespace-nowrap text-sm font-bold tracking-tight text-[var(--text-primary)]">{kpi.label}</span>
                <span className="whitespace-nowrap text-sm font-mono tabular-nums font-medium text-[var(--text-secondary)]">{kpi.value}</span>
              </div>

              {isOpen ? (
                <div className="absolute left-0 right-auto top-full z-50 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-2xl border border-[var(--border-accent)] bg-[var(--surface-elevated)] p-4 shadow-xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-200 sm:right-auto sm:left-0">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`h-2 w-2 rounded-full ${colors.dot}`} aria-hidden="true" />
                        <div className="truncate text-xs font-semibold text-[var(--text-muted)]">{kpi.label}</div>
                      </div>
                      <div className="mt-1 text-lg font-bold font-mono tabular-nums text-[var(--text-primary)]">{kpi.value}</div>
                      {kpi.trend ? <div className={`mt-1 text-sm font-medium leading-snug ${colors.badge}`}>{kpi.trend}</div> : null}
                    </div>
                  </div>
                  {showSpark && kpi.trend_points ? (
                    <div className="mt-4 border-t border-[var(--border)] pt-4">
                      <div className="mb-2 text-[10px] font-semibold text-[var(--text-muted)]">Recent trend</div>
                      <div className="h-10 w-full overflow-hidden rounded-md opacity-90">
                        <Sparkline points={kpi.trend_points} statusColor={colors.stroke} width={250} height={40} />
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
