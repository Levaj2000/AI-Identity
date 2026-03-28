import { Link } from "react-router";
import { blogPosts } from "../data/blog-posts";

export default function Blog() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">
              Insights & Updates
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            The AI Identity <span className="text-[rgb(166,218,255)]">Journal</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[600px] mx-auto">
            Engineering trust and transparency for the autonomous agent economy.
            Deep dives into forensics, governance, and the future of agentic
            infrastructure.
          </p>
        </div>
      </section>

      {/* Posts */}
      <section className="pb-24 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto space-y-6">
          {blogPosts.map((post) => (
            <Link
              key={post.slug}
              to={`/blog/${post.slug}`}
              className="block group"
            >
              <article className="bg-white/[0.03] border border-white/10 rounded-2xl p-8 transition-all hover:border-[rgb(166,218,255)]/30 hover:bg-white/[0.05]">
                {/* Tags */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {post.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2.5 py-1 bg-[rgb(166,218,255)]/10 text-[rgb(166,218,255)] text-xs font-medium rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                {/* Title */}
                <h2 className="text-xl font-bold text-white mb-3 group-hover:text-[rgb(166,218,255)] transition-colors">
                  {post.title}
                </h2>

                {/* Excerpt */}
                <p className="text-sm text-gray-400 leading-relaxed mb-4">
                  {post.excerpt}
                </p>

                {/* Meta */}
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>{post.date}</span>
                  <span>&middot;</span>
                  <span>{post.readTime}</span>
                  <span className="ml-auto text-[rgb(166,218,255)] opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                    Read more
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </span>
                </div>
              </article>
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}
