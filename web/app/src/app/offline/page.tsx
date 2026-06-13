export const metadata = { title: "Offline — paced.coach" };

export default function OfflinePage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--surface)] text-3xl">
        📡
      </div>
      <h1 className="mb-2 text-xl font-bold text-[var(--text-primary)]">
        You&apos;re offline
      </h1>
      <p className="max-w-sm text-sm text-[var(--text-secondary)]">
        paced.coach needs an internet connection to load your training data and
        coaching insights. Please reconnect and try again.
      </p>
    </div>
  );
}
