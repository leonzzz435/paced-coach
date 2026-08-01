import PublicPageShell from "@/components/public_page_shell";
import { buildPublicMetadata } from "@/lib/public-metadata";

export const metadata = buildPublicMetadata({
  title: "Terms of Use — paced.coach",
  description: "Terms for using the local-first paced.coach app.",
  path: "/terms",
});

export default function TermsPage() {
  return (
    <PublicPageShell title="Terms of Use" subtitle="Terms for using the local-first paced.coach app.">
      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">1. Provider and Scope</h2>
        <p>These terms apply to the paced.coach local-first open-source build.</p>
        <p>
          The service provider is Leon Zajchowski, operating under the business name paced.coach, Petersauer Strasse
          34, 68307 Mannheim, Germany.
        </p>
        <p>The source code is provided under the project license. These terms do not replace the license terms.</p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">2. Service Description</h2>
        <p>
          paced.coach provides software for endurance training context management, plan generation, and coaching chat.
        </p>
        <p>The app does not provide medical, therapeutic, or diagnostic advice.</p>
        <p>Outputs depend on the context you declare and the language-model service you configure.</p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">3. Local Access and Credentials</h2>
        <p>
          The default build is a no-login single-user app intended for localhost. You are responsible for securing your
          local environment, database, API keys, OAuth credentials, and connected provider accounts.
        </p>
        <p>Credentials must not be committed to source control or shared with third parties.</p>
        <p>You may only connect training data sources that you are authorized to use.</p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">4. Local Build Only</h2>
        <p>The current local-first open-source build does not include in-app payment flows.</p>
        <p>
          If a hosted service is introduced later, commercial terms, provider roles, cancellation terms, and
          required consumer information must be reviewed and published before that launch.
        </p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">5. Usage Limits and Technical Controls</h2>
        <p>
          Some features may be subject to local safety controls, cooldowns, retry guards, or provider rate limits.
          These controls protect data integrity, service stability, local cost exposure, and external provider limits.
        </p>
        <p>These controls are local safety controls in the local-first build.</p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">6. User Obligations</h2>
        <p>The app may only be used lawfully and in line with these terms and third-party provider terms.</p>
        <p>
          Prohibited conduct includes abuse, manipulation, automated attacks, circumvention of safeguards, and unlawful
          content or data access.
        </p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">7. Liability and Health Context</h2>
        <p>Training suggestions are for guidance only and do not replace professional medical advice.</p>
        <p>Users make their own decisions about training volume, intensity, recovery, and safety.</p>
        <p>
          Statutory liability rules apply. In cases of slight negligence, liability is limited to breach of essential
          contractual obligations and foreseeable typical damages.
        </p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">8. Third-Party Providers and Changes</h2>
        <p>The app may depend on the configured LLM provider, optional LangSmith tracing, and local infrastructure.</p>
        <p>
          Outages, rate limits, API changes, or account restrictions at those providers may affect data freshness or
          feature availability.
        </p>
        <p>Features may change as the open-source project evolves.</p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">9. Local Data Reset</h2>
        <p>
          Local data reset is available from Settings only after the operator enables the explicit reset flags. The
          reset removes user-scoped app data and any legacy connector records from the local application database.
        </p>
        <p>Version 2.2.0 does not perform external training-data imports.</p>
      </section>

      <section className="space-y-3 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">10. Final Provisions</h2>
        <p>German law applies, excluding the United Nations Convention on Contracts for the International Sale of Goods.</p>
        <p>Mandatory consumer protection provisions of your country of residence remain unaffected.</p>
      </section>

      <p className="text-xs text-zinc-500">
        Operational draft for external legal review — not legal advice. Last updated: August 1, 2026.
      </p>
    </PublicPageShell>
  );
}
