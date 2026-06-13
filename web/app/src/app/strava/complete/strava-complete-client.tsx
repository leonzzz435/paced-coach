"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

type Props = {
  connected: string | null;
  oauthError: string | null;
};

function resolveTargetPath({ connected, oauthError }: Props): string {
  if (connected === "strava") {
    return "/app/settings?connected=strava";
  }
  if (oauthError === "strava") {
    return "/app/settings?oauth_error=strava";
  }
  return "/app/settings";
}

function resolveCopy({ connected }: Props): { title: string; body: string } {
  if (connected === "strava") {
    return {
      title: "Finishing Strava connection",
      body: "We are taking you back to Settings.",
    };
  }
  return {
    title: "Strava connection needs attention",
    body: "We are sending you back to Settings so you can retry the reconnect flow.",
  };
}

export default function StravaCompleteClient(props: Props) {
  const router = useRouter();
  const targetPath = resolveTargetPath(props);
  const copy = resolveCopy(props);

  useEffect(() => {
    router.replace(targetPath);
  }, [router, targetPath]);

  return (
    <main className="min-h-screen bg-[var(--background)] px-6 py-16 text-[var(--text-primary)]">
      <div className="mx-auto max-w-md rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-8 shadow-sm">
        <h1 className="text-2xl font-semibold tracking-tight">{copy.title}</h1>
        <p className="mt-3 text-sm text-[var(--text-secondary)]">{copy.body}</p>
        <div className="mt-6 flex flex-wrap gap-3 text-sm font-semibold">
          <Link className="rounded-full bg-[var(--accent-primary)] px-4 py-2 text-white" href={targetPath}>
            Continue
          </Link>
        </div>
      </div>
    </main>
  );
}
