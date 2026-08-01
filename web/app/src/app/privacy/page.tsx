import Link from "next/link";
import PublicPageShell from "@/components/public_page_shell";
import { buildPublicMetadata } from "@/lib/public-metadata";

export const metadata = buildPublicMetadata({
  title: "Privacy Policy — paced.coach",
  description: "How the local-first paced.coach app handles training and coaching data.",
  path: "/privacy",
});

export default function PrivacyPage() {
  return (
    <PublicPageShell title="Privacy Policy" subtitle="Local-first privacy notes for paced.coach.">
      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">1. Local Operator and Project Contact</h2>
        <p>
          The person who installs and operates this open-source app controls its local database and configuration. The
          project maintainer does not receive that local data merely because the software is installed.
        </p>
        <p>Project contact: Leon Zajchowski, paced.coach, Petersauer Strasse 34, 68307 Mannheim, Germany</p>
        <p>
          Contact: <span className="font-mono">support@paced.coach</span>
        </p>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">2. Data Categories</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Local owner compatibility fields used by the single-user app</li>
          <li>Profile data, athlete context, goals, races, constraints, and training preferences</li>
          <li>Analysis, plan, and coaching outputs generated in the app</li>
          <li>
            Local Head Coach checkpoints containing resumable working context, plan drafts, model messages, tool
            results, and clarification state
          </li>
          <li>Technical logs created by your local runtime</li>
          <li>Support communications if you choose to contact the maintainer</li>
        </ul>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">3. Purposes and Legal Bases</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Running the local app and creating coaching outputs under the local operator&apos;s chosen legal basis</li>
          <li>Security, stability, and local safety controls (GDPR Art. 6(1)(f))</li>
          <li>Compliance with legal obligations where applicable (GDPR Art. 6(1)(c))</li>
          <li>Health-related training data requires an applicable GDPR Art. 9 condition where the GDPR applies</li>
        </ul>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">4. Recipients and Processors</h2>
        <p>
          In a local-first open-source build, processor use depends on how you configure and run the software. The
          following categories may apply when you configure the related services:
        </p>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <strong>Storage and hosting:</strong> your local machine by default, or infrastructure selected by the
            operator if they deploy it elsewhere.
          </li>
          <li>
            <strong>Authentication:</strong> local owner mode by default. The public local-first setup does not require
            hosted login.
          </li>
          <li>
            <strong>AI inference:</strong> OpenAI receives the prompt context required for plan generation and coaching.
          </li>
          <li>
            <strong>Optional observability:</strong> LangSmith only if <code>LANGSMITH_API_KEY</code> is configured.
            Traces may contain prompt and response content.
          </li>
        </ul>
        <p className="mt-2">We do not sell personal data.</p>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">5. AI Transparency</h2>
        <p>
          Athlete-provided profile, goal, race, constraint, plan, and coach-chat context may be sent to OpenAI to
          generate analysis, a season roadmap, a 28-day plan, and coaching responses.
        </p>
        <p>
          Version 2.2.0 does not connect to external activity or recovery-data providers. It must not present missing
          device evidence as known fact.
        </p>
        <p>
          The app is intended to provide coaching support and training guidance. It is not intended to make fully
          automated decisions with legal or similarly significant effects.
        </p>
        <p>
          Local stored data can be removed with the local privacy reset after you intentionally enable the reset flag.
        </p>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">6. International Transfers</h2>
        <p>
          External AI providers or optional observability providers may operate outside the EU/EEA.
          Operators should review transfer safeguards before any hosted or production use.
        </p>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">7. Retention</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Local content data remains in your local Postgres database until you delete or reset it.</li>
          <li>
            Checkpoints for completed, failed, or cancelled Head Coach runs remain in local Postgres for seven days by
            default, then scheduled cleanup removes them. In-progress and awaiting-input checkpoints remain available
            so the run can resume.
          </li>
          <li>
            In local mode, the privacy reset removes user-scoped app data, owner-scoped checkpoint payloads, and legacy
            connector rows while preserving the technical local owner row.
          </li>
          <li>Legal retention exceptions may apply where required by law.</li>
          <li>Backup copies may continue to contain historical snapshots until overwritten by the operator.</li>
        </ul>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">8. Cookies and Tracking</h2>
        <p>
          paced.coach currently relies on essential local application technologies. Hosted analytics are not required
          for the local-first setup.
        </p>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">9. Your Rights</h2>
        <p>
          You have rights to access, rectification, erasure, restriction, data portability, and objection. You can
          withdraw consent at any time with effect for the future.
        </p>
        <p>
          You can also lodge a complaint with a data protection supervisory authority, especially in your place of
          residence or the place of the alleged infringement.
        </p>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">10. Deletion and Contact</h2>
        <p>
          Deletion details are available on{" "}
          <Link className="text-zinc-900 underline" href="/delete">
            Local Data Reset
          </Link>
          . For support and privacy requests, use{" "}
          <Link className="text-zinc-900 underline" href="/support">
            Support
          </Link>
          .
        </p>
      </section>

      <p className="text-xs text-zinc-500">Operational draft — last updated: August 1, 2026</p>
    </PublicPageShell>
  );
}
