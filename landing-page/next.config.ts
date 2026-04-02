import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Framer components need transpilation
  transpilePackages: ["unframer"],


  // Source directory
  // Next.js will look for app/ inside src/
  // since we have our code in src/

  async redirects() {
    return [
      // non-www → www
      {
        source: "/:path*",
        has: [{ type: "host", value: "ai-identity.co" }],
        destination: "https://www.ai-identity.co/:path*",
        permanent: true,
      },
      // Old domain redirects
      {
        source: "/:path*",
        has: [{ type: "host", value: "aiforensic.tech" }],
        destination: "https://www.ai-identity.co/:path*",
        permanent: true,
      },
      {
        source: "/:path*",
        has: [{ type: "host", value: "www.aiforensic.tech" }],
        destination: "https://www.ai-identity.co/:path*",
        permanent: true,
      },
      {
        source: "/:path*",
        has: [{ type: "host", value: "aiforensictech.com" }],
        destination: "https://www.ai-identity.co/:path*",
        permanent: true,
      },
      {
        source: "/:path*",
        has: [{ type: "host", value: "www.aiforensictech.com" }],
        destination: "https://www.ai-identity.co/:path*",
        permanent: true,
      },
    ];
  },

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
