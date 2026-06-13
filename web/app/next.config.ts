import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    externalDir: true,
  },
  async redirects() {
    return [
      {
        source: "/:path*",
        has: [{ type: "host", value: "www.paced.coach" }],
        destination: "https://paced.coach/:path*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
