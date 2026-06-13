import Link from "next/link";

type Props = {
  title: string;
  subtitle?: string;
  backHref?: string;
  children: React.ReactNode;
};

export default function PublicPageShell({ title, subtitle, backHref = "/", children }: Props) {
  return (
    <main className="min-h-screen bg-zinc-50 p-8 text-zinc-900">
      <div className="mx-auto max-w-3xl space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
            {subtitle ? <p className="text-sm text-zinc-600">{subtitle}</p> : null}
          </div>
          <Link className="rounded-md border bg-white px-3 py-2 text-sm text-zinc-700 hover:text-zinc-900" href={backHref}>
            Back
          </Link>
        </header>

        {children}
      </div>
    </main>
  );
}

