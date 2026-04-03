import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: "/" },
      { userAgent: "GPTBot", allow: "/" },
      { userAgent: "Google-Extended", allow: "/" },
      { userAgent: "ClaudeBot", allow: "/" },
      { userAgent: "PerplexityBot", allow: "/" },
      { userAgent: "Anthropic-ai", allow: "/" },
      { userAgent: "Bytespider", allow: "/" },
    ],
    sitemap: "https://www.ai-identity.co/sitemap.xml",
  };
}
