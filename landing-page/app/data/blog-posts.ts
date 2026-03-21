export interface BlogPost {
  slug: string;
  title: string;
  date: string;
  readTime: string;
  excerpt: string;
  tags: string[];
  sections: { heading: string; content: string[] }[];
}

export const blogPosts: BlogPost[] = [
  {
    slug: "why-ai-agents-need-identity",
    title: "Why AI Agents Need Identity",
    date: "March 21, 2026",
    readTime: "6 min read",
    excerpt:
      "AI agents are moving from demos to production, but there's a fundamental gap: no standard way to verify who — or what — an agent is. Here's why that needs to change.",
    tags: ["AI Agents", "Identity", "Infrastructure"],
    sections: [
      {
        heading: "The Agent Revolution Is Here",
        content: [
          "In the last eighteen months, AI agents have gone from research demos to production workloads. Companies are deploying agents that book meetings, process invoices, manage infrastructure, and negotiate with other agents on their behalf.",
          "But there's a problem hiding in plain sight: none of these agents have a verifiable identity.",
          "When a human logs into a system, there's a well-established chain of trust — usernames, passwords, multi-factor authentication, OAuth tokens, session cookies. Decades of infrastructure ensure that when someone says they're Alice from Acme Corp, the system can verify that claim.",
          "AI agents have none of this. Most operate with shared API keys, hardcoded credentials, or no authentication at all. In a world where agents are making decisions and taking actions autonomously, this isn't just an inconvenience — it's a security crisis waiting to happen.",
        ],
      },
      {
        heading: "The Problem with API Keys",
        content: [
          "The most common approach today is giving agents an API key and calling it done. But API keys were designed for server-to-server communication, not for autonomous entities that make independent decisions.",
          "An API key tells you which application is making a request. It doesn't tell you which agent within that application is acting, what permissions that specific agent should have, whether the agent has been revoked or compromised, or who is responsible for the agent's actions.",
          "When something goes wrong — and in production, things always go wrong — you need answers to all of these questions. API keys can't give them to you.",
        ],
      },
      {
        heading: "What Agent Identity Looks Like",
        content: [
          "Agent identity isn't just authentication with a different name. It's a fundamentally different problem that requires new thinking.",
          "A proper agent identity system needs to answer four questions. First, authentication: is this agent who it claims to be? Second, authorization: what is this agent allowed to do? Third, accountability: who deployed this agent and who is responsible for its actions? Fourth, auditability: what has this agent done, and can we prove it?",
          "These questions become even more complex in multi-agent systems, where agents from different organizations need to interact. How does Company A's purchasing agent verify that Company B's sales agent is legitimate? How do you enforce spending limits across organizational boundaries?",
        ],
      },
      {
        heading: "Why Now",
        content: [
          "The window for establishing agent identity standards is narrow. Right now, the ecosystem is small enough that ad-hoc solutions work. But as agent deployments scale from hundreds to millions, the lack of identity infrastructure will become a critical bottleneck.",
          "Enterprises are already asking the right questions: How do we govern our agents? How do we audit their actions? How do we revoke access when an agent is compromised? These questions don't have good answers yet — but they will, and the companies that build that infrastructure now will define how the agent economy works.",
          "That's why we built AI Identity. Not because identity is exciting — but because without it, the autonomous agent future everyone is building toward simply won't work.",
        ],
      },
    ],
  },
  {
    slug: "compliance-in-the-age-of-autonomous-ai",
    title: "Compliance in the Age of Autonomous AI",
    date: "March 18, 2026",
    readTime: "5 min read",
    excerpt:
      "Existing compliance frameworks weren't built for AI agents. As enterprises deploy autonomous systems, the gap between what regulators expect and what companies can prove is growing fast.",
    tags: ["Compliance", "Enterprise", "Governance"],
    sections: [
      {
        heading: "The Compliance Gap",
        content: [
          "Every enterprise compliance framework assumes one thing: that a human is making decisions. SOC 2 controls reference authorized personnel. HIPAA requires individuals to acknowledge data access. Financial regulations demand personal accountability for transactions.",
          "AI agents break all of these assumptions. When an agent autonomously processes a healthcare claim, who acknowledged the data access? When an agent executes a financial transaction, who is personally accountable? When an auditor asks for access logs, can you show which agent accessed what data and why?",
          "Most companies deploying AI agents today cannot answer these questions. They're operating in a compliance gray zone — technically functional, but one audit away from a serious problem.",
        ],
      },
      {
        heading: "What Regulators Are Starting to Ask",
        content: [
          "Regulatory bodies are catching up. The EU AI Act requires transparency about AI systems making consequential decisions. US financial regulators are publishing guidance on AI governance. Industry-specific frameworks are being updated to account for autonomous systems.",
          "The common thread across all of these is accountability. Regulators want to know who deployed an agent, what it's authorized to do, what it actually did, and whether appropriate controls were in place.",
          "Companies that can answer these questions clearly and with evidence will have a significant advantage. Companies that can't will face increasing regulatory friction.",
        ],
      },
      {
        heading: "The Three Pillars of Agent Compliance",
        content: [
          "Based on conversations with enterprises deploying AI agents, we see three core requirements emerging.",
          "The first is scoped permissions. Every agent should operate under the principle of least privilege. A customer service agent shouldn't have access to financial systems. A data analysis agent shouldn't be able to modify production databases. Permissions should be granular, enforceable, and auditable.",
          "The second is tamper-proof audit trails. Every action an agent takes should be logged with its identity, timestamp, the action performed, and the policy that authorized it. These logs need to be immutable — you can't prove compliance if the evidence can be altered.",
          "The third is policy enforcement at the infrastructure level. Compliance can't depend on agents behaving correctly. It needs to be enforced at the gateway level, before requests reach their destination. If an agent exceeds its permissions, the request should be blocked, logged, and flagged — automatically.",
        ],
      },
      {
        heading: "Building for the Compliance-First Future",
        content: [
          "The companies that will win in enterprise AI aren't necessarily the ones with the best models or the fastest inference. They're the ones that can deploy AI agents in regulated environments with confidence.",
          "This means investing in identity and governance infrastructure now, before regulators mandate it. It means treating compliance not as a checkbox exercise but as a competitive advantage.",
          "At AI Identity, we're building the infrastructure that makes this possible — per-agent identity, scoped permissions, tamper-proof audit trails, and policy enforcement at the gateway level. Because the future of enterprise AI isn't just about what agents can do. It's about proving what they did.",
        ],
      },
    ],
  },
];
