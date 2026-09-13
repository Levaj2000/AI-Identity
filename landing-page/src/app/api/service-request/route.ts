import { NextResponse } from "next/server";
import { Resend } from "resend";

/**
 * Request-for-Services intake API route.
 *
 * Receives advisory service requests from /request-services and forwards
 * each one as an email to the founder (reply-to set to the requester).
 * No mailing-list state, no persistence — the email is the record.
 *
 * Rate limiting mirrors the probe-signup route: best-effort, in-memory,
 * 5 submissions per IP per hour.
 */

const SERVICES = new Map([
  ["intro-call", "Intro Call — $50"],
  ["evidence-review", "Evidence Architecture Review — $750"],
  ["build-advisory", "Verifiable Build Advisory — $1,500/month"],
  ["verifier-enablement", "Verifier Enablement — $2,500"],
]);

const FROM = "AI Identity <noreply@ai-identity.co>";
const TO = "jeff@ai-identity.co";

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

type ServiceRequestBody = {
  name?: string;
  email?: string;
  company?: string;
  role?: string;
  service?: string;
  goal?: string;
  timeline?: string;
  budget?: string;
  description?: string;
  heardAbout?: string;
  paidAcknowledged?: boolean;
};

function clean(v: unknown, max = 500): string {
  return typeof v === "string" ? v.trim().slice(0, max) : "";
}

export async function POST(req: Request) {
  let body: ServiceRequestBody;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "invalid_json" }, { status: 400 });
  }

  const name = clean(body.name, 120);
  const email = clean(body.email, 254).toLowerCase();
  const company = clean(body.company, 160);
  const role = clean(body.role, 120);
  const service = clean(body.service, 60);
  const goal = clean(body.goal, 120);
  const timeline = clean(body.timeline, 60);
  const budget = clean(body.budget, 60);
  const description = clean(body.description, 4000);
  const heardAbout = clean(body.heardAbout, 300);
  const paidAcknowledged = body.paidAcknowledged === true;

  if (!name || !emailRegex.test(email) || !company || !description) {
    return NextResponse.json({ error: "missing_required" }, { status: 400 });
  }
  if (!SERVICES.has(service)) {
    return NextResponse.json({ error: "invalid_service" }, { status: 400 });
  }
  if (!paidAcknowledged) {
    return NextResponse.json({ error: "paid_not_acknowledged" }, { status: 400 });
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
    // Fail-soft: don't block UX on backend misconfig. Log and 202.
    console.error("RESEND_API_KEY not set — service request not delivered", {
      service,
      ip_partial: ip.slice(0, 7),
    });
    return NextResponse.json({ ok: true, delivered: false }, { status: 202 });
  }

  const resend = new Resend(apiKey);
  const now = new Date();
  const serviceLabel = SERVICES.get(service) ?? service;

  try {
    await resend.emails.send({
      from: FROM,
      to: TO,
      replyTo: email,
      subject: `Service request: ${serviceLabel} — ${company}`,
      text: [
        `New advisory service request`,
        ``,
        `Service:     ${serviceLabel}`,
        `Name:        ${name}`,
        `Email:       ${email}`,
        `Company:     ${company}`,
        `Role:        ${role || "—"}`,
        `Goal:        ${goal || "—"}`,
        `Timeline:    ${timeline || "—"}`,
        `Budget:      ${budget || "—"}`,
        `Heard about: ${heardAbout || "—"}`,
        ``,
        `What they need:`,
        description,
        ``,
        `IP (raw):   ${ip}`,
        `Timestamp:  ${now.toISOString()}`,
        ``,
        `Reply directly to this email to reach the requester.`,
      ].join("\n"),
    });
    return NextResponse.json({ ok: true, delivered: true }, { status: 200 });
  } catch (err) {
    console.error("Resend send failed (service-request)", {
      service,
      message: err instanceof Error ? err.message : String(err),
    });
    return NextResponse.json({ ok: true, delivered: false }, { status: 202 });
  }
}
