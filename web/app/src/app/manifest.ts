import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "paced.coach — adaptive endurance coaching",
    short_name: "paced.coach",
    description:
      "Current fitness analysis, a season roadmap, a 28-day training block, and an adaptive coach built from your training and recovery data.",
    start_url: "/app",
    display: "standalone",
    background_color: "#0b0f19",
    theme_color: "#0b0f19",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/favicon.svg", sizes: "any", type: "image/svg+xml" },
    ],
  };
}
