import Link from "next/link";
import PublicPageShell from "@/components/public_page_shell";
import { buildPublicMetadata } from "@/lib/public-metadata";

export const metadata = buildPublicMetadata({
  title: "Support — paced.coach",
  description: "Support, privacy requests, and data controls for paced.coach.",
  path: "/support",
});

export default function SupportPage() {
  return (
    <PublicPageShell title="Support" subtitle="Contact, privacy requests, and data controls.">
      <section className="rounded-lg border bg-white p-6 space-y-3 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">Contact</h2>
        <p>
          Email: <span className="font-mono">support@paced.coach</span>
        </p>
        <p>Do not include API keys, OAuth secrets, database dumps, or private training exports in support messages.</p>
      </section>

      <section className="rounded-lg border bg-white p-6 space-y-3 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">Response Time</h2>
        <p>We aim to respond as soon as reasonably possible.</p>
        <p>Privacy requests under GDPR are handled within applicable legal deadlines.</p>
      </section>

      <section className="rounded-lg border bg-white p-6 space-y-3 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">Common Requests</h2>
        <ul className="list-disc pl-5 space-y-1">
          <li>Local setup and development issues</li>
          <li>Local privacy reset or data deletion questions</li>
          <li>Access and export requests for stored data</li>
          <li>Training data source connection or sync issues</li>
          <li>Technical bugs and security reports</li>
        </ul>
      </section>

      <section className="rounded-lg border bg-white p-6 space-y-3 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">Local Build Support</h2>
        <p>The current local-first build does not include in-app payment support.</p>
        <p>For setup issues, include the app version, operating system, and the relevant error message without secrets.</p>
        <p>For security issues, follow the private reporting guidance in the repository `SECURITY.md`.</p>
      </section>

      <section className="rounded-lg border bg-white p-6 space-y-3 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">Reset Local Data</h2>
        <p>
          Local reset details are available on{" "}
          <Link className="underline text-zinc-900" href="/delete">
            Local Data Reset
          </Link>
          . Additional privacy details are in the{" "}
          <Link className="underline text-zinc-900" href="/privacy">
            Privacy Policy
          </Link>
          .
        </p>
      </section>

      <p className="text-xs text-zinc-500">Last updated: May 31, 2026</p>
    </PublicPageShell>
  );
}
