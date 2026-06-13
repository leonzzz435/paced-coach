import { redirect } from "next/navigation";

import { buildPublicMetadata } from "@/lib/public-metadata";

export const metadata = buildPublicMetadata({
  title: "paced.coach - local-first AI endurance coach",
  description: "Run paced.coach locally for your own training plans, coach history, and optional connected data.",
  path: "/",
});

export default function Home() {
  redirect("/app");
}
