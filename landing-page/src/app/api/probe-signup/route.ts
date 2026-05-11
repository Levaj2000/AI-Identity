import { NextResponse } from "next/server";
import { Resend } from "resend";
import { getProbeDb } from "@/lib/mongodb";

/**
 * Probe-page email-capture API route.
 *
 * Replaces the broken Buttondown integration (the slug never existed —
 * embed POSTs returned 404 silently because the client used mode:no-cors).
 *
 * Forwards each capture as an email to the founder so they can do the
 * targeted follow-up that Decision #45 (publication strategy) is built on.
 * No mailing-list state — the founder said they don't want a newsletter
 * cadence; they want named-prospect follow-up after each signup.
 */

const ALLOWED_PROBES = new Set([
  "ai-forensics-standalone", // Milestone #48
  "pqc-readiness", // Milestone #49
  "finance-compliance-pack", // Milestone #50
  "newsletter", // Footer form — kept so the form keeps working, no newsletter cadence implied
]);

const FROM = "AI Identity <noreply@ai-identity.co>";
const TO = "jeff@ai-identity.co";

// Best-effort IP rate-limit: 5 signups per IP per hour. Won't survive
// serverless instance restarts, but stops casual flooding. Real abuse
// protection would need a durable store (Vercel KV, Upstash). Good
// enough for probe-scale traffic.
const rateLimitWindow = 60 * 60 * 1000; // 1 hour
const rateLimitMax = 5;
const ipHits = new Map<string, number[]>();

function isOverLimit(ip: string): boolean {
  const now = Date.now();
  const hits = (ipHits.get(ip) ?? []).filter((t) => now - t < rateLimitWindow);
  if (hits.length >= rateLimitMax) {
    ipHits.set(ip, hits);
    return true;
  }
  hits.push(now);
  ipHits.set(ip, hits);
  return false;
}

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(req: Request) {
  let body: { email?: string; probe?: string; source?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const email = (body.email ?? "").trim().toLowerCase();
  const probe = (body.probe ?? "").trim();
  const source = (body.source ?? "direct").trim().slice(0, 200);

  if (!emailRegex.test(email)) {
    return NextResponse.json({ error: "invalid_email" }, { status: 400 });
  }
  if (!ALLOWED_PROBES.has(probe)) {
    return NextResponse.json({ error: "invalid_probe" }, { status: 400 });
  }

  const ip =
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    req.headers.get("x-real-ip") ??
    "unknown";
  if (isOverLimit(ip)) {
    return NextResponse.json({ error: "rate_limited" }, { status: 429 });
  }

  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) {
    // Fail-soft: don't block the user's UX on backend misconfig. The
    // Vercel Analytics email_captured event already fired client-side,
    // so the conversion signal is preserved. Log and 202.
    console.error("RESEND_API_KEY not set — signup not delivered to inbox", {
      probe,
      ip_partial: ip.slice(0, 7),
    });
    return NextResponse.json({ ok: true, delivered: false }, { status: 202 });
  }

  const resend = new Resend(apiKey);
  const userAgent = req.headers.get("user-agent") ?? "unknown";
  const now = new Date();

  // Best-effort persistence for the daily summary cron. Never blocks the
  // user-facing path on Mongo state — if MONGODB_URI is unset or the write
  // fails, we log and proceed. The Resend email is still sent and Vercel
  // Analytics has already fired the conversion event.
  try {
    const db = await getProbeDb();
    if (db) {
      await db.collection("signups").insertOne({
        email,
        probe,
        source,
        ip_prefix: ip.split(".").slice(0, 2).join(".") || ip.slice(0, 12),
        user_agent: userAgent.slice(0, 300),
        created_at: now,
      });
    }
  } catch (err) {
    console.error("Mongo insert failed (continuing)", {
      probe,
      message: err instanceof Error ? err.message : String(err),
    });
  }

  try {
    await resend.emails.send({
      from: FROM,
      to: TO,
      replyTo: email,
      subject: `[Probe: ${probe}] New signup — ${email}`,
      text: [
        `New signup on ${probe}`,
        "",
        `Email:      ${email}`,
        `Source:     ${source}`,
        `IP (raw):   ${ip}`,
        `User-Agent: ${userAgent}`,
        `Timestamp:  ${now.toISOString()}`,
        "",
        "Reply directly to this email to reach the prospect.",
        "",
        "Refs: Decision #45 (publication strategy), Milestones #48/#49/#50.",
      ].join("\n"),
    });
    return NextResponse.json({ ok: true, delivered: true }, { status: 200 });
  } catch (err) {
    console.error("Resend send failed", {
      probe,
      message: err instanceof Error ? err.message : String(err),
    });
    // Fail-soft same as missing API key — analytics event already fired.
    return NextResponse.json({ ok: true, delivered: false }, { status: 202 });
  }
}
