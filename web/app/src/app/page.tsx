import { redirect } from "next/navigation";

import { buildPublicMetadata } from "@/lib/public-metadata";

export const metadata = buildPublicMetadata({
  title: "paced.coach - a complete AI endurance coach",
  description:
    "Turn your goals, availability, and constraints into a season roadmap, 28-day plan, and coach chat with your own LLM key. No wearable required.",
  path: "/",
});

export default function Home() {
  redirect("/app");
}
