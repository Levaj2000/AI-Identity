import { Helmet } from "react-helmet-async";

const BASE_URL = "https://www.ai-identity.co";
const SITE_NAME = "AI Identity";
const DEFAULT_OG_IMAGE = `${BASE_URL}/images/og-default.png`;
const TWITTER_HANDLE = "@AIIdentityCo";

interface SEOProps {
  title: string;
  description: string;
  path: string;
  ogType?: "website" | "article";
  ogImage?: string;
  article?: {
    publishedTime: string;
    modifiedTime?: string;
    author?: string;
    tags?: string[];
  };
  jsonLd?: Record<string, unknown> | Record<string, unknown>[];
  noIndex?: boolean;
}

export default function SEO({
  title,
  description,
  path,
  ogType = "website",
  ogImage,
  article,
  jsonLd,
  noIndex = false,
}: SEOProps) {
  const canonicalUrl = `${BASE_URL}${path === "/" ? "" : path}`;
  const fullTitle = path === "/" ? title : `${title} | ${SITE_NAME}`;
  const image = ogImage || DEFAULT_OG_IMAGE;

  return (
    <Helmet>
      {/* Core meta */}
      <title>{fullTitle}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={canonicalUrl} />
      {noIndex && <meta name="robots" content="noindex,nofollow" />}

      {/* Open Graph */}
      <meta property="og:type" content={ogType} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:url" content={canonicalUrl} />
      <meta property="og:site_name" content={SITE_NAME} />
      <meta property="og:image" content={image} />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />
      <meta property="og:image:alt" content={title} />

      {/* Article-specific OG tags */}
      {article?.publishedTime && (
        <meta property="article:published_time" content={article.publishedTime} />
      )}
      {article?.modifiedTime && (
        <meta property="article:modified_time" content={article.modifiedTime} />
      )}
      {article?.author && (
        <meta property="article:author" content={article.author} />
      )}
      {article?.tags?.map((tag) => (
        <meta property="article:tag" content={tag} key={tag} />
      ))}

      {/* Twitter Card */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:site" content={TWITTER_HANDLE} />
      <meta name="twitter:creator" content={TWITTER_HANDLE} />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={image} />

      {/* JSON-LD Structured Data */}
      {jsonLd && (
        <script type="application/ld+json">
          {JSON.stringify(
            Array.isArray(jsonLd) ? jsonLd : jsonLd,
            null,
            0
          )}
        </script>
      )}
    </Helmet>
  );
}

// ─── Pre-built JSON-LD schemas ───────────────────────────────────────────────

export const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "AI Identity",
  url: BASE_URL,
  logo: `${BASE_URL}/images/logo.png`,
  description:
    "AI Identity is an identity infrastructure platform for autonomous AI agents. It provides per-agent API keys, scoped permissions, policy-as-code enforcement, and tamper-proof cryptographic audit trails.",
  sameAs: [
    "https://twitter.com/AIIdentityCo",
    "https://www.linkedin.com/company/ai-identity",
    "https://github.com/Levaj2000/AI-Identity",
  ],
  foundingDate: "2026",
  founder: {
    "@type": "Person",
    name: "Jeff Leva",
  },
};

export const softwareApplicationSchema = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "AI Identity",
  applicationCategory: "SecurityApplication",
  operatingSystem: "Web",
  description:
    "Identity infrastructure for AI agents. Per-agent API keys, scoped permissions, tamper-proof audit trails, and compliance dashboards for SOC 2, EU AI Act, NIST AI RMF, and GDPR.",
  url: BASE_URL,
  offers: [
    {
      "@type": "Offer",
      name: "Free",
      price: "0",
      priceCurrency: "USD",
      description: "Up to 5 agents — perfect for prototyping",
    },
    {
      "@type": "Offer",
      name: "Pro",
      price: "79",
      priceCurrency: "USD",
      description: "Up to 50 agents — for teams in production",
      priceValidUntil: "2027-12-31",
    },
    {
      "@type": "Offer",
      name: "Business",
      price: "299",
      priceCurrency: "USD",
      description: "Up to 200 agents — advanced requirements",
      priceValidUntil: "2027-12-31",
    },
  ],
  featureList: [
    "Per-agent API keys with scoped permissions",
    "HMAC-SHA256 tamper-proof audit trails",
    "Policy-as-code enforcement",
    "EU AI Act compliance dashboard",
    "SOC 2 Type II alignment",
    "Chain-of-thought forensic replay",
    "Human-in-the-loop approval gates",
    "Real-time anomaly detection",
    "Zero-trust gateway architecture",
  ],
};

export const websiteSchema = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "AI Identity",
  url: BASE_URL,
  description:
    "Identity infrastructure for autonomous AI agents. Per-agent API keys, scoped permissions, and tamper-proof audit trails.",
  potentialAction: {
    "@type": "SearchAction",
    target: `${BASE_URL}/blog?q={search_term_string}`,
    "query-input": "required name=search_term_string",
  },
};

export function makeArticleSchema(post: {
  title: string;
  slug: string;
  date: string;
  excerpt: string;
  readTime: string;
}) {
  return {
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    headline: post.title,
    description: post.excerpt,
    url: `${BASE_URL}/blog/${post.slug}`,
    datePublished: new Date(post.date).toISOString(),
    dateModified: new Date(post.date).toISOString(),
    author: {
      "@type": "Person",
      name: "Jeff Leva",
      url: "https://www.linkedin.com/in/jeffleva",
    },
    publisher: {
      "@type": "Organization",
      name: "AI Identity",
      url: BASE_URL,
      logo: {
        "@type": "ImageObject",
        url: `${BASE_URL}/images/logo.png`,
      },
    },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": `${BASE_URL}/blog/${post.slug}`,
    },
    image: `${BASE_URL}/images/og-default.png`,
    wordCount: post.readTime.includes("10") ? 2500 : 1800,
  };
}

export function makeHowToSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: "How to Set Up AI Agent Identity and Governance in 15 Minutes",
    description:
      "AI Identity is a transparent gateway between your agents and LLM providers. No SDK lock-in, no agent code changes. Just change one URL.",
    totalTime: "PT15M",
    step: [
      {
        "@type": "HowToStep",
        position: 1,
        name: "Register Your Agents",
        text: "Give each AI agent a unique, cryptographic identity. Every agent gets a verifiable fingerprint with scoped API keys and automated key rotation.",
        url: `${BASE_URL}/how-it-works#register`,
      },
      {
        "@type": "HowToStep",
        position: 2,
        name: "Define Policies",
        text: "Set fine-grained access controls per agent. Control which models an agent can call, enforce rate limits, set token budgets, and define time-of-day restrictions.",
        url: `${BASE_URL}/how-it-works#policies`,
      },
      {
        "@type": "HowToStep",
        position: 3,
        name: "Route Through the Gateway",
        text: "Point your agents at the AI Identity gateway instead of calling LLM providers directly. One line of code. The gateway handles authentication, policy enforcement, and logging.",
        url: `${BASE_URL}/how-it-works#gateway`,
      },
      {
        "@type": "HowToStep",
        position: 4,
        name: "Monitor and Audit",
        text: "Every request is logged with a tamper-proof, HMAC-SHA256 hash-chained audit trail. View real-time dashboards, run compliance assessments, and export forensic evidence.",
        url: `${BASE_URL}/how-it-works#audit`,
      },
    ],
  };
}
