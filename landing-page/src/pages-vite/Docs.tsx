import { useState, useEffect } from "react";
import { docSections } from "../data/docs-content";
import type { DocBlock } from "../data/docs-content";
import SEO from "../components/SEO";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute right-3 top-3 rounded-md border border-white/10 bg-[rgb(16,19,28)] px-2.5 py-1 text-xs font-medium text-gray-400 transition-colors hover:bg-white/10 hover:text-white"
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}

function CodeBlock({
  language,
  title,
  body,
}: {
  language: string;
  title?: string;
  body: string;
}) {
  return (
    <div className="my-4 rounded-xl border border-white/5 overflow-hidden">
      {title && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-[rgb(16,19,28)] border-b border-white/5">
          <span className="text-xs font-mono text-[rgb(166,218,255)]/80">
            {language}
          </span>
          <span className="text-xs text-gray-500">{title}</span>
        </div>
      )}
      <div className="relative">
        <pre className="overflow-x-auto bg-[rgb(16,19,28)] p-4 text-sm leading-relaxed">
          <code className="text-gray-300 font-mono">{body}</code>
        </pre>
        <CopyButton text={body} />
      </div>
    </div>
  );
}

function CardIcon({ name }: { name?: string }) {
  const cls = "w-4 h-4 text-[rgb(166,218,255)]";
  switch (name) {
    case "fingerprint":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 10v4M7.5 7.5A7.5 7.5 0 0 1 19.5 12v0M4.5 12a7.5 7.5 0 0 1 3-6M16.5 16.5A7.5 7.5 0 0 1 4.5 12M19.5 12a7.5 7.5 0 0 1-3 6" />
        </svg>
      );
    case "shield":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      );
    case "check":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    case "search":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
        </svg>
      );
    case "key":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
        </svg>
      );
    case "bot":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="8" width="18" height="12" rx="2" /><path d="M12 2v6M9 15h.01M15 15h.01" />
        </svg>
      );
    default:
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" /><path d="M12 8v4l3 3" />
        </svg>
      );
  }
}

function renderBlock(block: DocBlock, index: number) {
  switch (block.type) {
    case "text":
      return (
        <p key={index} className="text-gray-400 leading-relaxed my-4">
          {block.body}
        </p>
      );

    case "code":
      return (
        <CodeBlock
          key={index}
          language={block.language}
          title={block.title}
          body={block.body}
        />
      );

    case "steps":
      return (
        <div key={index} className="space-y-8 my-6">
          {block.items.map((step, i) => (
            <div
              key={i}
              className="border-l-2 border-[rgb(166,218,255)]/30 pl-6"
            >
              <h3 className="text-lg font-semibold text-white mb-2">
                {step.title}
              </h3>
              <p className="text-gray-400 text-sm leading-relaxed mb-3">
                {step.description}
              </p>
              {step.code && (
                <div className="relative rounded-xl border border-white/5 overflow-hidden">
                  <pre className="overflow-x-auto bg-[rgb(16,19,28)] p-4 text-sm leading-relaxed">
                    <code className="text-gray-300 font-mono">
                      {step.code}
                    </code>
                  </pre>
                  <CopyButton text={step.code} />
                </div>
              )}
            </div>
          ))}
        </div>
      );

    case "cards":
      return (
        <div
          key={index}
          className="grid grid-cols-1 sm:grid-cols-2 gap-4 my-6"
        >
          {block.items.map((card, i) => (
            <div
              key={i}
              className="rounded-xl border border-white/5 bg-[rgb(16,19,28)]/60 p-6"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-lg bg-[rgb(166,218,255)]/10 flex items-center justify-center">
                  <CardIcon name={card.icon} />
                </div>
                <h3 className="text-base font-semibold text-white">
                  {card.title}
                </h3>
              </div>
              <p className="text-sm text-gray-400 leading-relaxed">
                {card.description}
              </p>
            </div>
          ))}
        </div>
      );

    case "links":
      return (
        <div key={index} className="grid grid-cols-1 sm:grid-cols-2 gap-4 my-6">
          {block.items.map((link, i) => (
            <a
              key={i}
              href={link.href}
              target="_blank"
              rel="noopener noreferrer"
              className="group rounded-xl border border-white/5 bg-[rgb(16,19,28)]/60 p-6 hover:border-[rgb(166,218,255)]/30 transition-colors"
            >
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-base font-semibold text-white group-hover:text-[rgb(166,218,255)] transition-colors">
                  {link.label}
                </h3>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="text-gray-500 group-hover:text-[rgb(166,218,255)] transition-colors"
                >
                  <path d="M7 17L17 7M17 7H7M17 7v10" />
                </svg>
              </div>
              <p className="text-sm text-gray-400 leading-relaxed">
                {link.description}
              </p>
            </a>
          ))}
        </div>
      );

    default:
      return null;
  }
}

export default function Docs() {
  const [activeSection, setActiveSection] = useState(docSections[0].id);

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY + 150;
      for (let i = docSections.length - 1; i >= 0; i--) {
        const el = document.getElementById(docSections[i].id);
        if (el && el.offsetTop <= scrollY) {
          setActiveSection(docSections[i].id);
          return;
        }
      }
      setActiveSection(docSections[0].id);
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="pt-[72px]">
      <SEO
        title="Documentation — AI Identity API & SDK"
        description="API reference, SDK guides, and integration documentation for AI Identity. Get started in 15 minutes with per-agent keys and audit trails."
        path="/docs"
      />
      {/* Header */}
      <section className="px-6 md:px-12 pt-16 pb-10">
        <div className="max-w-[1100px] mx-auto">
          <div className="mb-2 px-3 py-1 inline-block border border-[rgb(166,218,255)]/30 rounded-full text-[rgb(166,218,255)] text-xs font-medium tracking-widest uppercase">
            Documentation
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-white mt-4 mb-4">
            Build with <span className="text-[rgb(166,218,255)]">AI Identity</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-2xl">
            Everything you need to add identity, policy enforcement, and
            forensic logging to your AI agents.
          </p>
        </div>
      </section>

      {/* Main layout */}
      <div className="max-w-[1100px] mx-auto px-6 md:px-12 pb-24 flex gap-12">
        {/* Sidebar TOC */}
        <aside className="hidden md:block w-56 shrink-0">
          <nav className="sticky top-[120px] space-y-1">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              On this page
            </p>
            {docSections.map((section) => (
              <button
                key={section.id}
                onClick={() => scrollTo(section.id)}
                className={`block w-full text-left px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  activeSection === section.id
                    ? "text-[rgb(166,218,255)] bg-[rgb(166,218,255)]/5 font-medium"
                    : "text-gray-500 hover:text-gray-300"
                }`}
              >
                {section.title}
              </button>
            ))}
            <div className="border-t border-white/5 mt-4 pt-4">
              <a
                href="https://api.ai-identity.co/redoc"
                target="_blank"
                rel="noopener noreferrer"
                className="block px-3 py-1.5 text-sm text-gray-500 hover:text-[rgb(166,218,255)] transition-colors"
              >
                API Reference &rarr;
              </a>
              <a
                href="https://dashboard.ai-identity.co"
                target="_blank"
                rel="noopener noreferrer"
                className="block px-3 py-1.5 text-sm text-gray-500 hover:text-[rgb(166,218,255)] transition-colors"
              >
                Dashboard &rarr;
              </a>
            </div>
          </nav>
        </aside>

        {/* Content */}
        <main className="flex-1 min-w-0">
          {/* Mobile TOC */}
          <div className="md:hidden mb-8 rounded-xl border border-white/5 bg-[rgb(16,19,28)]/60 p-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              On this page
            </p>
            <div className="flex flex-wrap gap-2">
              {docSections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => scrollTo(section.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                    activeSection === section.id
                      ? "text-[rgb(166,218,255)] bg-[rgb(166,218,255)]/10 font-medium"
                      : "text-gray-500 bg-white/5 hover:text-gray-300"
                  }`}
                >
                  {section.title}
                </button>
              ))}
            </div>
          </div>

          {docSections.map((section, sectionIdx) => (
            <section
              key={section.id}
              id={section.id}
              className={sectionIdx > 0 ? "mt-16 pt-12 border-t border-white/5" : ""}
            >
              <h2 className="text-2xl md:text-3xl font-bold text-white mb-6">
                {section.title}
              </h2>
              {section.content.map((block, blockIdx) =>
                renderBlock(block, blockIdx),
              )}
            </section>
          ))}
        </main>
      </div>
    </div>
  );
}
