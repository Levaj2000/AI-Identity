import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Framer components need transpilation
  transpilePackages: ["unframer"],


  // Source directory
  // Next.js will look for app/ inside src/
  // since we have our code in src/

  async redirects() {
    return [
      // /ai-forensics consolidated into /forensics (canonical deep-dive page)
      {
        source: "/ai-forensics",
        destination: "/forensics",
        permanent: true,
      },
      // Near-duplicate of /industries/finance consolidated there (SEC/FINRA/
      // MiFID II content merged into the industry page). 301 keeps backlinks
      // and indexed URLs alive.
      {
        source: "/use-cases/financial-compliance",
        destination: "/industries/finance",
        permanent: true,
      },
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

  async rewrites() {
    return [
      // Case File bundles exported before #379 tell recipients to curl the
      // JWKS from this host (without -L, so a redirect would save the wrong
      // body). Proxy the live key set so those bundles keep verifying.
      {
        source: "/.well-known/ai-identity-public-keys.json",
        destination:
          "https://api.ai-identity.co/.well-known/ai-identity-public-keys.json",
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
