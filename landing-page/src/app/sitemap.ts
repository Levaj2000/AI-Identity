import type { MetadataRoute } from "next";
import { blogPosts } from "@/data/blog-posts";

const BASE_URL = "https://www.ai-identity.co";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date().toISOString().split("T")[0];

  const staticPages: MetadataRoute.Sitemap = [
    { url: `${BASE_URL}/`, lastModified: now, changeFrequency: "weekly", priority: 1.0 },
    { url: `${BASE_URL}/product`, lastModified: now, changeFrequency: "weekly", priority: 0.95 },
    { url: `${BASE_URL}/how-it-works`, lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: `${BASE_URL}/eu-ai-act-checklist`, lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: `${BASE_URL}/pricing`, lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: `${BASE_URL}/architecture`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/security`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/forensics`, lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: `${BASE_URL}/changelog`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${BASE_URL}/integrations`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/docs`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/blog`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    // Use cases
    { url: `${BASE_URL}/use-cases/customer-support`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/use-cases/coding-assistant`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/use-cases/financial-compliance`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    // Industries
    { url: `${BASE_URL}/industries/finance`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/industries/healthcare`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    // Comparisons
    { url: `${BASE_URL}/vs/opal`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/vs/valence`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/vs/holistic-ai`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/vs/portkey`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/vs/credo-ai`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${BASE_URL}/vs/traditional-iam`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    // Tools
    { url: `${BASE_URL}/roi-calculator`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    // Company
    { url: `${BASE_URL}/about`, lastModified: now, changeFrequency: "monthly" as const, priority: 0.8 },
    { url: `${BASE_URL}/contact`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: `${BASE_URL}/careers`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${BASE_URL}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.4 },
    { url: `${BASE_URL}/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.4 },
  ];

  const blogPages: MetadataRoute.Sitemap = blogPosts.map((post) => ({
    url: `${BASE_URL}/blog/${post.slug}`,
    lastModified: new Date(post.date).toISOString().split("T")[0],
    changeFrequency: "monthly" as const,
    priority: 0.7,
  }));

  return [...staticPages, ...blogPages];
}
