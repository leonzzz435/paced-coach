import Link from "next/link";
import PublicPageShell from "@/components/public_page_shell";
import { buildPublicMetadata } from "@/lib/public-metadata";

export const metadata = buildPublicMetadata({
  title: "Local Data Reset — paced.coach",
  description: "How local data reset works in the local-first paced.coach app.",
  path: "/delete",
});

type DeleteDataPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function readFirst(value: string | string[] | undefined): string | null {
  if (typeof value === "string") return value;
  if (Array.isArray(value) && value.length > 0 && typeof value[0] === "string") return value[0];
  return null;
}

export default async function DeleteDataPage({ searchParams }: DeleteDataPageProps) {
  const resolvedParams = (await searchParams) ?? {};
  const status = readFirst(resolvedParams.status);
  const authCleanup = readFirst(resolvedParams.auth_cleanup);

  return (
    <PublicPageShell title="Local Data Reset" subtitle="How local app data deletion works.">
      {status === "reset" ? (
        <section className="rounded-lg border border-emerald-200 bg-emerald-50 p-6 text-sm text-emerald-900">
          <h2 className="text-lg font-medium">Local data reset completed</h2>
          <p className="mt-2">
            User-scoped local app data and connector credentials were removed from the active local database. The
            technical local owner row was preserved so the app can continue to start cleanly.
          </p>
        </section>
      ) : null}

      {status === "deleted" ? (
        <section
          className={`rounded-lg border p-6 text-sm ${
            authCleanup === "pending"
              ? "border-amber-200 bg-amber-50 text-amber-900"
              : "border-emerald-200 bg-emerald-50 text-emerald-900"
          }`}
        >
          <h2 className="text-lg font-medium">
            {authCleanup === "pending" ? "Local data deleted" : "Account deletion completed"}
          </h2>
          <p className="mt-2">
            {authCleanup === "pending"
              ? "Local paced.coach data was deleted. Hosted sign-in cleanup still needs follow-up."
              : "Local paced.coach data and the associated hosted sign-in identity were deleted from the active system."}
          </p>
        </section>
      ) : null}

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">1. Before Resetting</h2>
        <p>Back up your database if you may want to keep your plans, profile, races, or coaching history.</p>
        <p>
          Do not run <code>docker compose down -v</code> unless you intentionally want to delete the local Postgres
          volume.
        </p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">2. Enable Reset</h2>
        <p>Local reset is disabled by default. To enable it, set both flags intentionally:</p>
        <pre className="overflow-x-auto rounded bg-zinc-950 p-4 text-xs text-zinc-50">
          <code>{"ALLOW_LOCAL_DATA_DELETE=true\nNEXT_PUBLIC_ALLOW_LOCAL_DATA_DELETE=true"}</code>
        </pre>
        <p>Restart the API and web app after changing these values.</p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">3. Scope of Reset</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Athlete profile, competitions, and local owner-scoped app content</li>
          <li>Active plans, analyses, jobs, daily update runs, weekly recap runs, and coaching outputs</li>
          <li>Coach threads, messages, events, proposals, and local safety usage rows</li>
          <li>Stored Strava and WHOOP credentials, pending OAuth sessions, and connector history</li>
          <li>Local usage rows that still exist in the database</li>
        </ul>
        <p>The local technical owner row is preserved in local mode to avoid breaking `LOCAL_OWNER_USER_ID`.</p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">4. What May Remain</h2>
        <p>Database backups, local filesystem exports, logs, screenshots, and external provider records are separate.</p>
        <p>
          Disconnecting Strava or WHOOP removes local tokens and attempts provider-side revocation, but provider-held
          records remain governed by each provider&apos;s own controls and policies.
        </p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">5. Follow-Up Questions</h2>
        <p>
          For follow-up questions, use the{" "}
          <Link className="text-zinc-900 underline" href="/support">
            Support page
          </Link>
          .
        </p>
      </section>

      <p className="text-xs text-zinc-500">Last updated: May 31, 2026</p>
    </PublicPageShell>
  );
}
