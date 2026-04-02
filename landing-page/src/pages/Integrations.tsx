import { Link } from "react-router";
import SEO from "../components/SEO";

const providers = [
  { name: "OpenAI", models: "GPT-4o, GPT-4o-mini, o1, o3" },
  { name: "Anthropic", models: "Claude Sonnet 4, Claude Opus, Claude Haiku" },
  { name: "Google", models: "Gemini 2.5 Pro, Gemini 2.5 Flash" },
  { name: "Cohere", models: "Command R+, Command R" },
  { name: "Mistral", models: "Mistral Large, Mistral Medium" },
  { name: "Custom", models: "Any OpenAI-compatible REST API" },
];

const frameworks = [
  {
    name: "LangChain",
    language: "Python",
    code: `from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o",
    base_url="https://ai-identity-gateway.onrender.com/v1",
    api_key="aid_sk_your_agent_key",
)`,
  },
  {
    name: "CrewAI",
    language: "Python",
    code: `import os
os.environ["OPENAI_API_BASE"] = \\
    "https://ai-identity-gateway.onrender.com/v1"
os.environ["OPENAI_API_KEY"] = "aid_sk_your_agent_key"

from crewai import Agent, Task, Crew
# ... agents work as normal`,
  },
  {
    name: "AutoGen",
    language: "Python",
    code: `config_list = [{
    "model": "gpt-4o",
    "base_url": "https://ai-identity-gateway.onrender.com/v1",
    "api_key": "aid_sk_your_agent_key",
}]`,
  },
  {
    name: "OpenAI SDK",
    language: "TypeScript",
    code: `import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://ai-identity-gateway.onrender.com/v1",
  apiKey: "aid_sk_your_agent_key",
});`,
  },
];

export default function Integrations() {
  return (
    <>
      {/* Hero */}
      <section className="pt-32 pb-16 px-6 md:px-12">
      <SEO
        title="AI Agent Integrations — OpenAI, Anthropic, Gemini & More"
        description="AI Identity works with every major LLM provider. Drop-in gateway integration with OpenAI, Anthropic, Google Gemini, and 100+ models. Change one URL."
        path="/integrations"
      />
        <div className="max-w-[900px] mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-[rgb(166,218,255)]/10 border border-[rgb(166,218,255)]/20 rounded-full mb-8">
            <span className="text-[rgb(166,218,255)] text-sm font-medium">Integrations</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-white mb-6 leading-tight">
            Works With Your{" "}
            <span className="text-[rgb(166,218,255)]">Entire Stack</span>
          </h1>
          <p className="text-lg text-gray-400 max-w-[640px] mx-auto leading-relaxed">
            AI Identity uses the OpenAI-compatible API format, so integration usually
            means changing one line — the base URL. Works with every major LLM provider
            and agent framework.
          </p>
        </div>
      </section>

      {/* Providers */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Supported Providers</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[500px] mx-auto">
            Route to any LLM provider through a single gateway. The model name in
            your request determines which upstream provider handles it.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {providers.map((provider) => (
              <div key={provider.name} className="bg-white/[0.03] border border-white/10 rounded-xl p-5 hover:border-[rgb(166,218,255)]/30 transition-all">
                <h3 className="text-base font-semibold text-white mb-1">{provider.name}</h3>
                <p className="text-xs text-gray-500">{provider.models}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Framework Examples */}
      <section className="pb-20 px-6 md:px-12">
        <div className="max-w-[900px] mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-3 text-center">Framework Examples</h2>
          <p className="text-sm text-gray-400 text-center mb-10 max-w-[500px] mx-auto">
            Drop-in compatible with all major agent frameworks. Change the base URL
            and your agents are governed.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {frameworks.map((fw) => (
              <div key={fw.name} className="rounded-xl border border-white/5 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-2.5 bg-[rgb(16,19,28)] border-b border-white/5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-[rgb(166,218,255)]/80">{fw.language}</span>
                    <span className="text-xs text-gray-500">{fw.name}</span>
                  </div>
                </div>
                <pre className="overflow-x-auto bg-[rgb(16,19,28)] p-4 text-xs leading-relaxed">
                  <code className="text-gray-300 font-mono">{fw.code}</code>
                </pre>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24 px-6 md:px-12">
        <div className="max-w-[800px] mx-auto">
          <div className="bg-[rgb(166,218,255)]/5 border border-[rgb(166,218,255)]/20 rounded-2xl p-8 text-center">
            <h2 className="text-xl md:text-2xl font-bold text-white mb-3">Ready to integrate?</h2>
            <p className="text-sm text-gray-400 mb-6 max-w-[500px] mx-auto">
              Check out the full documentation for detailed integration guides,
              or sign up and start routing in minutes.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <Link to="/docs" className="inline-flex items-center gap-2 px-6 py-3 bg-[rgb(166,218,255)] text-[rgb(4,7,13)] font-semibold rounded-xl hover:bg-[rgb(166,218,255)]/80 transition-colors">
                Read the Docs
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </Link>
              <a href="https://dashboard.ai-identity.co" className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-colors">
                Get Started Free
              </a>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
