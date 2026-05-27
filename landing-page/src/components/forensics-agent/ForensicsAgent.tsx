"use client";

import { useEffect, useRef, useState } from "react";

interface Citation {
  title: string;
  url: string | null;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  isError?: boolean;
}

const SUGGESTED_QUESTIONS = [
  "What is a DSSE attestation?",
  "How does the HMAC audit chain work?",
  "What does the verify CLI do?",
  "How do you handle key rotation?",
];

const INITIAL_GREETING =
  "Ask me about AI Identity's forensics primitives — audit chains, attestations, the verify CLI, or compliance posture. I only answer from our published docs.";

function newId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function ForensicsAgent() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (open && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [open, messages]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || sending) return;

    const userMsg: Message = { id: newId(), role: "user", text: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);

    try {
      const res = await fetch("/api/forensics/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMessages((prev) => [
          ...prev,
          {
            id: newId(),
            role: "assistant",
            text:
              data?.error ??
              "Something went wrong talking to the forensics agent.",
            isError: true,
          },
        ]);
        return;
      }
      setMessages((prev) => [
        ...prev,
        {
          id: newId(),
          role: "assistant",
          text: data.answer || "I don't have that in our forensics docs.",
          citations: data.citations ?? [],
        },
      ]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          id: newId(),
          role: "assistant",
          text: "Network error reaching the forensics agent. Try again in a moment.",
          isError: true,
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      {/* Floating launcher */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close forensics agent" : "Open forensics agent"}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full bg-[rgb(166,218,255)] px-5 py-3 text-sm font-semibold text-[rgb(4,7,13)] shadow-lg shadow-[rgb(166,218,255)]/20 transition-transform hover:scale-105 active:scale-95"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {open ? (
            <>
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </>
          ) : (
            <>
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </>
          )}
        </svg>
        {open ? "Close" : "Ask the docs"}
      </button>

      {/* Panel */}
      {open && (
        <div
          role="dialog"
          aria-label="Forensics knowledge agent"
          className="fixed bottom-24 right-6 z-40 flex h-[560px] w-[min(420px,calc(100vw-3rem))] flex-col overflow-hidden rounded-2xl border border-white/10 bg-[rgb(4,7,13)]/95 shadow-2xl backdrop-blur-xl"
        >
          <header className="border-b border-white/10 px-5 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">
                  Forensics Knowledge Agent
                </h2>
                <p className="mt-0.5 text-[11px] text-gray-400">
                  Grounded in AI Identity&apos;s published forensics docs
                </p>
              </div>
              <span className="rounded-full bg-[rgb(166,218,255)]/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-[rgb(166,218,255)]">
                Beta
              </span>
            </div>
          </header>

          <div
            ref={scrollRef}
            className="flex-1 space-y-4 overflow-y-auto px-5 py-4"
          >
            {messages.length === 0 && (
              <>
                <div className="rounded-xl bg-white/[0.03] p-3 text-sm leading-relaxed text-gray-300">
                  {INITIAL_GREETING}
                </div>
                <div className="flex flex-wrap gap-2">
                  {SUGGESTED_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      type="button"
                      disabled={sending}
                      onClick={() => send(q)}
                      className="rounded-full border border-white/10 bg-white/[0.02] px-3 py-1.5 text-xs text-gray-300 transition-colors hover:border-[rgb(166,218,255)]/40 hover:text-white disabled:opacity-50"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={
                  msg.role === "user"
                    ? "ml-6 rounded-xl bg-[rgb(166,218,255)]/10 px-3 py-2 text-sm text-white"
                    : msg.isError
                      ? "mr-6 rounded-xl border border-red-500/30 bg-red-500/5 px-3 py-2 text-sm text-red-200"
                      : "mr-6 rounded-xl bg-white/[0.04] px-3 py-2 text-sm leading-relaxed text-gray-200"
                }
              >
                <div className="whitespace-pre-wrap">{msg.text}</div>
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {msg.citations.slice(0, 6).map((c, i) =>
                      c.url ? (
                        <a
                          key={`${msg.id}-c-${i}`}
                          href={c.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="rounded-full border border-[rgb(166,218,255)]/30 bg-[rgb(166,218,255)]/5 px-2 py-0.5 text-[10px] text-[rgb(166,218,255)] hover:bg-[rgb(166,218,255)]/15"
                        >
                          {c.title}
                        </a>
                      ) : (
                        <span
                          key={`${msg.id}-c-${i}`}
                          className="rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[10px] text-gray-400"
                        >
                          {c.title}
                        </span>
                      ),
                    )}
                  </div>
                )}
              </div>
            ))}

            {sending && (
              <div className="mr-6 flex items-center gap-2 rounded-xl bg-white/[0.04] px-3 py-2 text-sm text-gray-400">
                <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[rgb(166,218,255)]" />
                <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[rgb(166,218,255)] [animation-delay:120ms]" />
                <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[rgb(166,218,255)] [animation-delay:240ms]" />
              </div>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              void send(input);
            }}
            className="border-t border-white/10 px-3 py-3"
          >
            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 focus-within:border-[rgb(166,218,255)]/40">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about audit chains, attestations, key rotation…"
                disabled={sending}
                maxLength={500}
                className="flex-1 bg-transparent text-sm text-white placeholder:text-gray-500 focus:outline-none disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!input.trim() || sending}
                className="rounded-md bg-[rgb(166,218,255)] px-3 py-1 text-xs font-semibold text-[rgb(4,7,13)] transition-opacity disabled:opacity-40"
              >
                Send
              </button>
            </div>
            <p className="mt-2 px-1 text-[10px] text-gray-500">
              Beta — verify critical answers against{" "}
              <a
                href="/blog"
                className="text-[rgb(166,218,255)] hover:underline"
              >
                our source docs
              </a>
              .
            </p>
          </form>
        </div>
      )}
    </>
  );
}
