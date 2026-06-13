import PublicPageShell from "@/components/public_page_shell";
import { buildPublicMetadata } from "@/lib/public-metadata";

export const metadata = buildPublicMetadata({
  title: "Impressum — paced.coach",
  description: "Provider information for paced.coach under Section 5 DDG.",
  path: "/impressum",
});

export default function ImpressumPage() {
  return (
    <PublicPageShell title="Impressum" subtitle="Information required under Section 5 DDG." backHref="/">
      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">Service Provider</h2>
        <p>Leon Zajchowski</p>
        <p>Business name: paced.coach</p>
        <p>Petersauer Strasse 34</p>
        <p>68307 Mannheim</p>
        <p>Germany</p>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">Contact</h2>
        <p>
          Email: <span className="font-mono">support@paced.coach</span>
        </p>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">Business and Tax Information</h2>
        <p>Trade registration (Gewerbeanmeldung): confirmed by the City of Mannheim on March 13, 2026.</p>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">Responsible for Content</h2>
        <p>Leon Zajchowski, address as listed above.</p>
      </section>

      <section className="space-y-2 rounded-lg border bg-white p-6 text-sm text-zinc-700">
        <h2 className="text-lg font-medium text-zinc-900">Consumer Dispute Resolution</h2>
        <p>We are not obliged and not willing to participate in dispute resolution proceedings before a consumer arbitration board.</p>
      </section>

      <p className="text-xs text-zinc-500">Last updated: April 9, 2026</p>
    </PublicPageShell>
  );
}
