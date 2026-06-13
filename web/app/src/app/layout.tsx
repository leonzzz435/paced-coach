import type { Viewport } from "next";
import "./globals.css";
import Footer from "@/components/footer";
import SwRegister from "@/components/sw-register";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
  themeColor: "#0b0f19",
};

export const metadata = {
  title: "paced.coach",
  description: "Connected endurance coaching for self-coached athletes.",
  metadataBase: new URL("https://paced.coach"),
  openGraph: {
    title: "paced.coach",
    description: "Connected endurance coaching for self-coached athletes.",
    url: "https://paced.coach",
    siteName: "paced.coach",
    images: [{ url: "/og.svg", width: 1200, height: 630, alt: "paced.coach" }],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "paced.coach",
    description: "Connected endurance coaching for self-coached athletes.",
    images: ["/og.svg"],
  },
  icons: {
    icon: "/favicon.svg",
    apple: "/icon-192.png",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "paced.coach",
  },
  other: {
    "mobile-web-app-capable": "yes",
  },
} as const;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <div className="min-h-screen flex flex-col">
          <div className="flex-1">{children}</div>
          <Footer />
        </div>
        <SwRegister />
      </body>
    </html>
  );
}
