import AppNav from "@/components/app-nav";
import CoachMessenger from "@/components/coach-chat/coach-messenger";
import MobileAccountMenu from "@/components/mobile-account-menu";
import { apiFetch } from "@/lib/api";
import type { AthleteProfileResponse, Competition, ProfilePayload } from "@/lib/types/athlete-context";
import {
  formatCompetitionsBadge,
  formatProfileCompletenessBadge,
} from "@/lib/types/athlete-context";

export default async function AppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  let profile: ProfilePayload | null = null;
  let competitionsCount = 0;

  const [profileResult, competitionsResult] = await Promise.allSettled([
    apiFetch<AthleteProfileResponse>("/api/athlete-profile"),
    apiFetch<Competition[]>("/api/competitions"),
  ]);

  if (profileResult.status === "fulfilled") {
    profile = profileResult.value.profile;
  }
  if (competitionsResult.status === "fulfilled") {
    competitionsCount = competitionsResult.value.length;
  }

  const profileBadge = formatProfileCompletenessBadge(profile, { available: profileResult.status === "fulfilled" });
  const competitionsBadge = formatCompetitionsBadge(
    competitionsResult.status === "fulfilled" ? competitionsCount : null,
    { available: competitionsResult.status === "fulfilled" },
  );
  const profileBadgeClass = profileResult.status === "fulfilled"
    ? "border-[var(--accent-primary)]/30 text-[var(--accent-primary)]"
    : "border-[var(--border-accent)] text-[var(--text-muted)]";
  const competitionsBadgeClass = competitionsResult.status === "fulfilled"
    ? "border-[var(--accent-warning)]/30 text-[var(--accent-warning)]"
    : "border-[var(--border-accent)] text-[var(--text-muted)]";

  return (
    <div className="flex h-dvh flex-col bg-[var(--background)] text-[var(--text-primary)] lg:flex-row lg:overflow-hidden">
      {/* Desktop Rail */}
      <AppNav variant="desktop-rail" />

      {/* Main viewport area */}
      <div className="flex min-w-0 flex-1 flex-col pt-4 lg:pt-6">
        <header className="mb-4 flex shrink-0 items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center gap-2 text-xs font-medium">
            <span className="rounded-full border border-[var(--accent-success)]/30 bg-[var(--surface)] px-2.5 py-1 text-[var(--accent-success)] shadow-sm">
              Provider-free
            </span>
            <span className={`rounded-full border bg-[var(--surface)] px-2.5 py-1 shadow-sm ${profileBadgeClass}`}>{profileBadge}</span>
            <span className={`rounded-full border bg-[var(--surface)] px-2.5 py-1 shadow-sm ${competitionsBadgeClass}`}>{competitionsBadge}</span>
          </div>
          {/* User button on mobile header */}
          <div className="lg:hidden">
            <MobileAccountMenu />
          </div>
        </header>

        <main className="min-w-0 flex-1 overflow-y-auto px-4 pb-20 sm:px-6 lg:px-8 lg:pb-6">
          {children}
        </main>
      </div>

      {/* Mobile Bottom Bar */}
      <AppNav variant="mobile-bottom" />

      <CoachMessenger />
    </div>
  );
}
