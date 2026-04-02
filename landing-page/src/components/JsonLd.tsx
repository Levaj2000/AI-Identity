/**
 * Server component that renders JSON-LD structured data inline.
 * This ensures structured data appears in the initial HTML served to crawlers.
 */
export default function JsonLd({
  data,
}: {
  data: Record<string, unknown> | Record<string, unknown>[];
}) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
