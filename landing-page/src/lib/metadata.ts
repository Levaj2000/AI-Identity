import type { Metadata } from "next";

const BASE_URL = "https://www.ai-identity.co";
const SITE_NAME = "AI Identity";
const DEFAULT_OG_IMAGE = "/images/og-image.png";
const TWITTER_HANDLE = "@ai_identity_co";

interface PageMetadataOptions {
  title: string;
  description: string;
  path: string;
  ogType?: "website" | "article";
  ogImage?: string;
  noIndex?: boolean;
  article?: {
    publishedTime?: string;
    modifiedTime?: string;
    tags?: string[];
    author?: string;
  };
}

export function generatePageMetadata({
  title,
  description,
  path,
  ogType = "website",
  ogImage,
  noIndex = false,
  article,
}: PageMetadataOptions): Metadata {
  const canonicalUrl = `${BASE_URL}${path === "/" ? "" : path}`;
  const image = ogImage || DEFAULT_OG_IMAGE;

  return {
    title,
    description,
    alternates: {
      canonical: canonicalUrl,
    },
    ...(noIndex && { robots: { index: false, follow: false } }),
    openGraph: {
      title,
      description,
      url: canonicalUrl,
      siteName: SITE_NAME,
      type: ogType,
      images: [{ url: image, width: 1200, height: 630, alt: title }],
      ...(article?.publishedTime && {
        publishedTime: article.publishedTime,
      }),
      ...(article?.modifiedTime && {
        modifiedTime: article.modifiedTime,
      }),
      ...(article?.tags && { tags: article.tags }),
    },
    twitter: {
      card: "summary_large_image",
      site: TWITTER_HANDLE,
      creator: TWITTER_HANDLE,
      title,
      description,
      images: [image],
    },
  };
}
