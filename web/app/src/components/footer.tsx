"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Footer() {
  const pathname = usePathname();
  if (pathname.startsWith("/app")) return null;

  return (
    <footer className="border-t bg-white">
      <div className="mx-auto max-w-5xl p-4 text-sm text-zinc-700 flex flex-wrap gap-4">
        <Link className="hover:text-zinc-900" href="/privacy">
          Privacy
        </Link>
        <Link className="hover:text-zinc-900" href="/terms">
          Terms
        </Link>
        <Link className="hover:text-zinc-900" href="/support">
          Support
        </Link>
        <Link className="hover:text-zinc-900" href="/delete">
          Delete Data
        </Link>
        <Link className="hover:text-zinc-900" href="/impressum">
          Impressum
        </Link>
      </div>
    </footer>
  );
}

