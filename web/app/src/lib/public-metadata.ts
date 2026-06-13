import type { Metadata } from "next";

type BuildPublicMetadataOptions = {
  description: string;
  path: string;
  title: string;
};

export function buildPublicMetadata(options: BuildPublicMetadataOptions): Metadata {
  return {
    title: options.title,
    description: options.description,
    alternates: {
      canonical: options.path,
    },
    openGraph: {
      title: options.title,
      description: options.description,
      url: `https://paced.coach${options.path}`,
      siteName: "paced.coach",
      images: [{ url: "/og.svg", width: 1200, height: 630, alt: "paced.coach" }],
      locale: "en_US",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: options.title,
      description: options.description,
      images: ["/og.svg"],
    },
  };
}
