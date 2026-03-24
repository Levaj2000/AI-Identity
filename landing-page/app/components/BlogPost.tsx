import { useParams, Link } from "react-router";
import Nav from "./landing/Nav";
import Footer from "./landing/Footer";
import { blogPosts } from "../data/blog-posts";

/**
 * Renders paragraph text with support for markdown-style inline links.
 * Converts [text](url) into styled <a> tags.
 */
function renderParagraph(text: string) {
  const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
  const parts: (string | JSX.Element)[] = [];
  let lastIndex = 0;
  let match;

  while ((match = linkRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const isExternal = match[2].startsWith("http");
    parts.push(
      <a
        key={match.index}
        href={match[2]}
        className="text-[#F59E0B] hover:underline"
        {...(isExternal
          ? { target: "_blank", rel: "noopener noreferrer" }
          : {})}
      >
        {match[1]}
      </a>
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}

export default function BlogPost() {
  const { slug } = useParams<{ slug: string }>();
  const post = blogPosts.find((p) => p.slug === slug);

  if (!post) {
    return (
      <div className="size-full bg-[#0a0a0b] overflow-auto">
        <Nav />
        <div className="pt-32 pb-24 px-6 text-center">
          <h1 className="text-3xl font-bold text-white mb-4">
            Post not found
          </h1>
          <Link to="/blog" className="text-[#F59E0B] hover:underline">
            ← Back to blog
          </Link>
        </div>
        <Footer />
      </div>
    );
  }

  return (
    <div className="size-full bg-[#0a0a0b] overflow-auto">
      <Nav />

      <article className="pt-32 pb-24 px-6 md:px-12">
        <div className="max-w-[700px] mx-auto">
          {/* Back link */}
          <Link
            to="/blog"
            className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-[#F59E0B] transition-colors mb-10"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Back to blog
          </Link>

          {/* Header */}
          <div className="mb-12">
            <div className="flex flex-wrap gap-2 mb-5">
              {post.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-2.5 py-1 bg-[#F59E0B]/10 text-[#F59E0B] text-xs font-medium rounded-full"
                >
                  {tag}
                </span>
              ))}
            </div>
            <h1 className="text-3xl md:text-4xl font-extrabold text-white mb-4 leading-tight">
              {post.title}
            </h1>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span>Jeff Leva</span>
              <span>·</span>
              <span>{post.date}</span>
              <span>·</span>
              <span>{post.readTime}</span>
            </div>
          </div>

          {/* Divider */}
          <div className="border-t border-white/10 mb-12" />

          {/* Content */}
          <div className="space-y-10">
            {post.sections.map((section, i) => (
              <section key={i}>
                <h2 className="text-xl font-bold text-white mb-4">
                  {section.heading}
                </h2>
                <div className="space-y-4">
                  {section.content.map((paragraph, j) => (
                    <p
                      key={j}
                      className="text-[15px] text-gray-300 leading-[1.8]"
                    >
                      {renderParagraph(paragraph)}
                    </p>
                  ))}
                </div>
              </section>
            ))}
          </div>

          {/* CTA */}
          <div className="mt-16 bg-[#F59E0B]/5 border border-[#F59E0B]/20 rounded-2xl p-8 text-center">
            <h3 className="text-lg font-bold text-white mb-2">
              Ready to secure your AI agents?
            </h3>
            <p className="text-sm text-gray-400 mb-6">
              Get started with AI Identity — deploy in 15 minutes, not 15
              weeks.
            </p>
            <a
              href="https://dashboard.ai-identity.co"
              className="inline-flex px-6 py-3 bg-[#F59E0B] text-[#0A0A0B] font-semibold rounded-xl hover:bg-[#F59E0B]/80 transition-colors"
            >
              Get Started Free →
            </a>
          </div>

          {/* Author */}
          <div className="mt-12 pt-8 border-t border-white/10 flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-[#F59E0B]/10 flex items-center justify-center text-[#F59E0B] font-bold text-lg">
              JL
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Jeff Leva</p>
              <p className="text-xs text-gray-500">
                Founder & CEO, AI Identity
              </p>
            </div>
          </div>
        </div>
      </article>

      <Footer />
    </div>
  );
}
