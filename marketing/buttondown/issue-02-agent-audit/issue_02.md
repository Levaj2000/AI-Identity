## Welcome back to Exhibit A.

Issue 01 was about DeepSeek — a model that arrived faster than the trust infrastructure around it. The argument was that the AI market keeps shipping powerful systems into real workflows before identity, policy, and forensics catch up.

This week's exhibit is closer to home. It's an AI agent. We built it. You can try it right now.

Go to [**ai-identity.co/forensics**](https://www.ai-identity.co/forensics), click "Ask the docs" in the corner, and ask it anything about AI forensics, audit chains, attestations, or the offline verify CLI. It will answer in two or three paragraphs and cite the published source for every claim.

It is a perfectly reasonable little marketing-site Q&A bot — not our customer product, a distinction that matters, and one I will come back to. It is also a perfect specimen of the gap we sell against.

---

# We Built an Agent. Then We Tried to Audit It.

Here is what is running under that widget:

- A retrieval system on a major cloud provider, indexed against our published forensics docs and blog posts.
- A grounded answer model that is configured to refuse anything not supported by the corpus.
- A service account with read-only access to the search index.
- A Workload Identity Federation bridge between our hosting provider and the cloud so no long-lived key sits anywhere.

By the standards of how most teams deploy agents today, this is a thoughtful build. It uses the right primitives in the right places. We are proud of it.

Now I am going to walk through the four questions every AI agent in production should be able to answer — and admit, on the record, that **our own agent can only answer two of them.**

## 1. Who built it, and who is it accountable to?

The agent runs under a specific service account. The service account has one role. The Workload Identity binding scopes the impersonation to a single project on a single hosting platform. So far, so good.

But "who built it" is not the same question as "who is it accountable to." If this agent answers a prospect's question with something subtly wrong, the accountability path runs back through our hosting provider's request logs, the cloud provider's audit logs, and our own application logs. Three separate vendors. Three different retention policies. Three different definitions of what counts as evidence.

That is not an accountability chain. That is a paper trail held together by trust in three different companies, none of which signed up to be your auditor.

> **Trust Root pillar:** Identity is not just a credential. It is a durable, attestable claim about which agent did what, that survives the agent, the vendor, and the deployment.

## 2. What is it allowed to do?

The policy that bounds our agent is one paragraph of text inside the function that calls the model. It says, roughly, "answer only from the indexed docs, refuse off-topic questions, never invent facts about our company."

Read that again. The policy is *a string in our source code.* It is enforced by the model honoring its own instructions. If a user crafts a prompt clever enough to override that string, the model will happily comply. There is no neutral party between the user input and the agent's behavior whose job it is to say no.

This is the default state of almost every agent shipping today. The "policy" is a system prompt, enforced at the model's discretion — not at an independent, recorded gate. That is the gap our gateway closes for customers; we just have not routed our own marketing-site widget through it yet.

> **Trust Root pillar:** Policy is not a sentence in a prompt. It is a fail-closed gate, evaluated by an independent component, that records its own decisions before the agent ever runs.

## 3. What did it actually say last Tuesday at 3pm?

This is the one our agent cannot answer at all.

I can pull request logs from our hosting provider and see that a POST request was made to the agent's endpoint. I can see the response status code and the latency. I cannot see what the user asked, what the agent retrieved, what context was assembled, what the model produced, or whether any of it has been altered in the logs since.

Our hosting provider's logs are mutable by design. Our cloud provider's audit logs cover their API calls, not our agent's outputs. The model's response was a string, sent over HTTP, and is now gone unless the user took a screenshot.

If a regulator, an angry enterprise prospect, or an internal compliance reviewer asked us "show me the conversation this agent had with customer X" — we couldn't. Not because we are negligent. Because the substrate we deployed on does not produce evidence. It produces logs.

> **Trust Root pillar:** Logs are not evidence. Evidence is what an outside party can verify without trusting the entity that produced it.

## 4. Can we prove the record hasn't been changed?

No.

There is no chain hash binding one response to the next. There is no signed attestation that commits to the agent's outputs over any window of time. If a hostile insider with database access decided to rewrite what the agent said yesterday, we would have no cryptographic way to detect it.

This is the gap our product closes for our customers — the gateway already ships the chain and the signed attestation. It is also, as of this writing, a gap in our own marketing-site widget.

> **Trust Root pillar:** Forensics is what turns a record into proof. A tamper-evident chain plus a KMS-signed attestation is the difference between "we say this happened" and "anyone can verify this happened."

---

## Why I am writing this in our own newsletter

Because there is no honest way to sell AI agent governance without acknowledging that we are early — including for ourselves. Every business in the next twelve months is going to deploy an agent that looks roughly like ours. Some will be slicker. Some will be sloppier. Almost none of them will be able to answer those four questions either.

We are building toward an AI ecosystem where agents transact, act, and decide on behalf of users at a scale we have not seen before. That ecosystem needs a trust root. Something that issues durable agent identities, attests to their actions, and produces evidence any outside party can verify.

We are building that. The Mandate Service that signs agent actions is on our roadmap. The HMAC-chained audit and DSSE-signed attestations already ship in our gateway. The next obvious step is to wire our own agent into the same controls — to sign every answer it gives, chain its outputs, and publish a verifier so anyone can audit it.

When that ships, this newsletter gets a follow-up: *The Agent on Our Site, Six Months Later.*

---

## The bottom line

*We built an AI agent. It is genuinely useful. This widget is not yet accountable in a way that would survive a hostile audit — and that is the market it lives in.*

*The controls that close this gap already ship in our gateway product. The widget is dogfood that has not eaten yet.*

---

## One question to take into your week

Open the agent your team deployed most recently — a chatbot, a copilot, a workflow agent, anything. Now answer those four questions about it:

1. **Who** — what durable identity ran it, and who is that identity accountable to?
2. **Policy** — what fail-closed gate decides what it can and cannot do?
3. **Record** — can you reconstruct, line by line, what it said to a specific user last Tuesday?
4. **Proof** — can you prove that reconstruction hasn't been altered?

If the honest answers are mostly "no" — that is the gap. You are not behind. You are the market.

---

### See you next week

Try the agent at [**ai-identity.co/forensics**](https://www.ai-identity.co/forensics). Break it. Ask it something hard. If you find something it gets wrong, hit reply — that is exactly the feedback loop we want.

If a friend forwarded this, [subscribe here](https://exhibit-a.ai-identity.co) so the next exhibit lands in your inbox.

**— Jeff**

*Jeff Leva is the founder of [AI Identity](https://ai-identity.co), building durable identity and tamper-evident forensics for AI agents.*
