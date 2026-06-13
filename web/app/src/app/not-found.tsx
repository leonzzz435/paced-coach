import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-zinc-50 p-8 text-zinc-900">
      <div className="space-y-3 text-center">
        <h1 className="text-2xl font-semibold">Not found</h1>
        <p className="text-sm text-zinc-600">This page doesn’t exist.</p>
        <Link
          href="/"
          className="inline-block text-sm font-medium text-zinc-900 underline underline-offset-4 hover:text-zinc-600"
        >
          Back to home
        </Link>
      </div>
    </main>
  );
}

