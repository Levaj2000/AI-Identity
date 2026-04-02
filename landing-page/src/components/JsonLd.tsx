import { useEffect } from "react";

interface JsonLdProps {
  data: Record<string, unknown> | Record<string, unknown>[];
}

/**
 * Injects JSON-LD structured data into the document head.
 * Cleans up on unmount to avoid duplicates during SPA navigation.
 */
export default function JsonLd({ data }: JsonLdProps) {
  useEffect(() => {
    const script = document.createElement("script");
    script.type = "application/ld+json";
    script.textContent = JSON.stringify(data);
    document.head.appendChild(script);

    return () => {
      document.head.removeChild(script);
    };
  }, [data]);

  return null;
}
