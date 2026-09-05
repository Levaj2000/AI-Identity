const pptxgen = require("pptxgenjs");

/* ------------------------------------------------------------------ *
 * AI Identity — DenAI Summit 2026 Startup Showcase deck (v4)
 * 8 slides, scripted for a 4–5 minute stage slot.
 * ------------------------------------------------------------------ */

const C = {
  ink: "0E1729", // deep navy-slate ground (dark slides)
  inkPanel: "1B2740", // raised panel on dark
  inkLine: "2C3B5C", // hairline on dark
  navy: "1E2761", // primary navy (light slides)
  ice: "CADCFC", // ice blue accent
  iceDeep: "7E9AD6", // ice blue, legible on light
  paper: "F4F6FA", // light ground
  card: "FFFFFF",
  cardEdge: "DDE3EE",
  mutedDark: "94A6C8", // muted text on dark
  mutedLight: "5B6883", // muted text on light
  allow: "1F8A5B",
  allowBg: "E6F4EC",
  deny: "B23B45",
  denyBg: "FAE9EA",
  flagBg: "FFF4E0", // placeholder / action-required tint
  flagEdge: "E3B45E",
  flagInk: "8A5A12",
};

const F = {
  head: "Cambria", // headers — gravitas, metric-safe
  body: "Calibri", // body
  mono: "Courier New", // signed-record voice
};

const W = 13.333;
const M = 0.75; // page margin
const CW = W - M * 2; // content width

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "AI Identity";
pres.company = "AI Identity";
pres.title = "AI Identity — DenAI Summit 2026 Showcase";

/* ---------------------------- helpers ---------------------------- */

const softShadow = () => ({
  type: "outer",
  color: "1E2761",
  blur: 12,
  offset: 2,
  angle: 90,
  opacity: 0.1,
});

function text(slide, str, o) {
  slide.addText(str, Object.assign({ isTextBox: true, margin: 0 }, o));
}

// Section title + deck (light slides)
function lightHead(slide, title, kicker, size) {
  text(slide, title, {
    x: M, y: 0.52, w: CW, h: 0.62,
    fontFace: F.head, fontSize: size || 34, bold: true, color: C.navy,
  });
  if (kicker) {
    text(slide, kicker, {
      x: M, y: 1.16, w: CW, h: 0.34,
      fontFace: F.body, fontSize: 15, color: C.mutedLight,
    });
  }
}

// The deck's one motif: a mono index chip (01 / 02 / ...)
function chip(slide, n, x, y, opts = {}) {
  const size = opts.size || 0.42;
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w: size, h: size, rectRadius: 0.08,
    fill: { color: opts.fill || C.navy },
    line: { color: opts.fill || C.navy, width: 0 },
  });
  text(slide, n, {
    x, y, w: size, h: size,
    fontFace: F.mono, fontSize: opts.fontSize || 11, bold: true,
    color: opts.color || "FFFFFF", align: "center", valign: "middle",
  });
}

function footer(slide, n) {
  text(slide, "AI Identity", {
    x: M, y: 6.92, w: 3, h: 0.26,
    fontFace: F.body, fontSize: 9.5, color: C.mutedLight,
  });
  text(slide, String(n).padStart(2, "0"), {
    x: W - M - 1, y: 6.92, w: 1, h: 0.26,
    fontFace: F.mono, fontSize: 9.5, color: C.mutedLight, align: "right",
  });
}

function footerDark(slide, n) {
  text(slide, "AI Identity", {
    x: M, y: 6.92, w: 3, h: 0.26,
    fontFace: F.body, fontSize: 9.5, color: C.mutedDark,
  });
  text(slide, String(n).padStart(2, "0"), {
    x: W - M - 1, y: 6.92, w: 1, h: 0.26,
    fontFace: F.mono, fontSize: 9.5, color: C.mutedDark, align: "right",
  });
}

/* =================================================================== *
 * 01 — Cover (dark)
 * =================================================================== */
{
  const s = pres.addSlide();
  s.background = { color: C.ink };

  text(s, "DENAI SUMMIT 2026   ·   STARTUP SHOWCASE", {
    x: M, y: 1.02, w: 7.2, h: 0.3,
    fontFace: F.mono, fontSize: 11, bold: true, color: C.iceDeep, charSpacing: 1.4,
  });

  text(s, "AI IDENTITY", {
    x: M, y: 1.5, w: 7.2, h: 0.68,
    fontFace: F.head, fontSize: 40, bold: true, color: "FFFFFF", charSpacing: 3,
  });

  text(s, "Accountable AI agents for public institutions", {
    x: M, y: 2.34, w: 7.0, h: 1.0,
    fontFace: F.head, fontSize: 27, color: C.ice, lineSpacing: 34,
  });

  text(
    s,
    "Cryptographic identity, policy enforcement, and evidence that can be verified independently.",
    {
      x: M, y: 3.5, w: 6.6, h: 0.8,
      fontFace: F.body, fontSize: 15, color: C.mutedDark, lineSpacing: 22,
    }
  );

  // hairline
  s.addShape(pres.ShapeType.line, {
    x: M, y: 4.72, w: 6.6, h: 0,
    line: { color: C.inkLine, width: 1 },
  });

  text(s, "Boulder, Colorado", {
    x: M, y: 4.96, w: 3.2, h: 0.3,
    fontFace: F.body, fontSize: 13, bold: true, color: "FFFFFF",
  });
  text(s, "Bootstrapped pre-seed  ·  working software today", {
    x: M, y: 5.32, w: 5.5, h: 0.3,
    fontFace: F.body, fontSize: 12.5, color: C.mutedDark,
  });
  text(s, "ai-identity.co", {
    x: M, y: 5.68, w: 3.2, h: 0.3,
    fontFace: F.mono, fontSize: 12.5, color: C.iceDeep,
  });

  // Right: a signed-record card — the motif, introduced on slide 1
  const px = 8.15, py = 1.72, pw = 4.43, ph = 4.32;
  s.addShape(pres.ShapeType.roundRect, {
    x: px, y: py, w: pw, h: ph, rectRadius: 0.06,
    fill: { color: C.inkPanel },
    line: { color: C.inkLine, width: 1 },
  });
  text(s, "ONE REQUEST, AS RECORDED", {
    x: px + 0.4, y: py + 0.36, w: pw - 0.8, h: 0.26,
    fontFace: F.mono, fontSize: 9.5, bold: true, color: C.iceDeep, charSpacing: 1.2,
  });

  const rows = [
    ["agent", "permitting-bot-04"],
    ["granted-by", "j.ruiz@city.example"],
    ["action", "purchase  $2,400"],
    ["policy", "ALLOW"],
    ["remaining", "$2,600 of $5,000"],
    ["record", "sha256:9f2c41a8…"],
  ];
  rows.forEach(([k, v], i) => {
    const ry = py + 0.98 + i * 0.48;
    text(s, k, {
      x: px + 0.4, y: ry, w: 1.25, h: 0.3,
      fontFace: F.mono, fontSize: 11, color: C.mutedDark,
    });
    text(s, v, {
      x: px + 1.65, y: ry, w: pw - 2.05, h: 0.3,
      fontFace: F.mono, fontSize: 11, bold: k === "policy",
      color: k === "policy" ? "4FD18B" : "FFFFFF",
    });
  });

  s.addShape(pres.ShapeType.line, {
    x: px + 0.4, y: py + 3.74, w: pw - 0.8, h: 0,
    line: { color: C.inkLine, width: 1 },
  });
  text(s, "verified offline  ·  no vendor call", {
    x: px + 0.4, y: py + 3.9, w: pw - 0.8, h: 0.3,
    fontFace: F.mono, fontSize: 10, color: "4FD18B",
  });

  s.addNotes(
    "0:00–0:20 — Open on the record card, not on the company. " +
      "'Every request an agent makes in a city should look like this: attributed, authorized, and provable.' " +
      "Say the company name once, then move."
  );
}

/* =================================================================== *
 * 02 — The hook / problem (dark)
 * =================================================================== */
{
  const s = pres.addSlide();
  s.background = { color: C.ink };

  text(s, "A city agent spends $40,000 at 2 a.m.", {
    x: M, y: 0.72, w: CW, h: 0.66,
    fontFace: F.head, fontSize: 36, bold: true, color: "FFFFFF",
  });
  text(
    s,
    "It used the shared service credential, like every other agent in the tenant. Monday morning, three questions have no answer.",
    {
      x: M, y: 1.46, w: 10.4, h: 0.6,
      fontFace: F.body, fontSize: 15, color: C.mutedDark, lineSpacing: 22,
    }
  );

  const cards = [
    {
      n: "01",
      label: "IDENTITY",
      q: "Which agent acted?",
      d: "Shared service credentials collapse many agents into one identity. The log names the service, not the actor.",
    },
    {
      n: "02",
      label: "AUTHORITY",
      q: "Was it authorized?",
      d: "Ordinary IAM does not express an agent's tool access, spending ceiling, or approval boundary.",
    },
    {
      n: "03",
      label: "EVIDENCE",
      q: "Will the record hold?",
      d: "Mutable application logs cannot prove that an event stayed complete and unaltered after the fact.",
    },
  ];

  const cw = 3.86, gap = 0.42, cy = 2.42, ch = 2.72;
  cards.forEach((c, i) => {
    const cx = M + i * (cw + gap);
    s.addShape(pres.ShapeType.roundRect, {
      x: cx, y: cy, w: cw, h: ch, rectRadius: 0.05,
      fill: { color: C.inkPanel },
      line: { color: C.inkLine, width: 1 },
    });
    chip(s, c.n, cx + 0.38, cy + 0.4, { fill: C.iceDeep, color: "0E1729" });
    text(s, c.label, {
      x: cx + 0.94, y: cy + 0.47, w: cw - 1.3, h: 0.28,
      fontFace: F.mono, fontSize: 10, bold: true, color: C.iceDeep, charSpacing: 1.2,
    });
    text(s, c.q, {
      x: cx + 0.38, y: cy + 1.06, w: cw - 0.76, h: 0.42,
      fontFace: F.head, fontSize: 20, bold: true, color: "FFFFFF",
    });
    text(s, c.d, {
      x: cx + 0.38, y: cy + 1.6, w: cw - 0.76, h: 1.0,
      fontFace: F.body, fontSize: 13, color: C.mutedDark, lineSpacing: 19,
    });
  });

  text(s, "Three unanswered questions become one public-trust problem.", {
    x: M, y: 5.52, w: CW, h: 0.44,
    fontFace: F.head, fontSize: 19, italic: true, color: C.ice,
  });

  footerDark(s, 2);
  s.addNotes(
    "0:20–1:00 — Land the scenario first, then the three questions. " +
      "These are governance questions before they are security questions: a resident asking 'who decided this?' " +
      "deserves an answer that does not depend on trusting a vendor's dashboard."
  );
}

/* =================================================================== *
 * 03 — The control path (light)
 * =================================================================== */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  lightHead(
    s,
    "Controls before the action, evidence after it",
    "The AI Identity control path — four stages on every request an agent makes.",
    32
  );

  const steps = [
    {
      n: "01",
      t: "Identity",
      d: "A unique cryptographic credential attributes every request to one agent, and to the human behind it.",
    },
    {
      n: "02",
      t: "Policy",
      d: "A fail-closed gateway evaluates permissions, spending limits, and approvals before the call leaves.",
    },
    {
      n: "03",
      t: "Compliance",
      d: "Control mappings connect each runtime decision to the review obligations auditors already ask about.",
    },
    {
      n: "04",
      t: "Forensics",
      d: "Signed, chained records support replay and independent verification months later.",
    },
  ];

  const cw = 2.83, gap = 0.32, cy = 1.86, ch = 3.06;
  steps.forEach((st, i) => {
    const cx = M + i * (cw + gap);
    s.addShape(pres.ShapeType.roundRect, {
      x: cx, y: cy, w: cw, h: ch, rectRadius: 0.05,
      fill: { color: C.card },
      line: { color: C.cardEdge, width: 1 },
      shadow: softShadow(),
    });
    chip(s, st.n, cx + 0.32, cy + 0.34);
    text(s, st.t, {
      x: cx + 0.32, y: cy + 0.98, w: cw - 0.64, h: 0.4,
      fontFace: F.head, fontSize: 21, bold: true, color: C.navy,
    });
    text(s, st.d, {
      x: cx + 0.32, y: cy + 1.5, w: cw - 0.64, h: 1.4,
      fontFace: F.body, fontSize: 13, color: C.mutedLight, lineSpacing: 19,
    });
    if (i < steps.length - 1) {
      text(s, "→", {
        x: cx + cw + 0.02, y: cy + 1.28, w: 0.28, h: 0.3,
        fontFace: F.body, fontSize: 15, color: C.iceDeep, align: "center",
      });
    }
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 5.26, w: CW, h: 1.06, rectRadius: 0.05,
    fill: { color: "E9EEF8" },
    line: { color: "D5DEEE", width: 1 },
  });
  text(s, "Nothing gets replaced.", {
    x: M + 0.42, y: 5.5, w: 3.0, h: 0.32,
    fontFace: F.head, fontSize: 16, bold: true, color: C.navy,
  });
  text(
    s,
    "The city keeps its existing AI applications, vendors, and services. AI Identity governs the requests between them.",
    {
      x: M + 3.5, y: 5.52, w: CW - 3.9, h: 0.6,
      fontFace: F.body, fontSize: 14, color: C.mutedLight, lineSpacing: 20,
    }
  );

  footer(s, 3);
  s.addNotes(
    "1:00–1:45 — Walk left to right once, one clause per stage. " +
      "The load-bearing sentence is the band at the bottom: this is not a rip-and-replace of anything the city has already procured."
  );
}

/* =================================================================== *
 * 04 — The working demonstration (light) — most airtime
 * =================================================================== */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  lightHead(
    s,
    "A procurement agent, under a delegated limit",
    "Working reference demonstration — product interface, demonstration environment."
  );

  // Left: the delegated authority
  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 1.86, w: 4.35, h: 3.46, rectRadius: 0.05,
    fill: { color: C.navy }, line: { color: C.navy, width: 0 },
  });
  text(s, "DELEGATED AUTHORITY", {
    x: M + 0.42, y: 2.16, w: 3.5, h: 0.28,
    fontFace: F.mono, fontSize: 10, bold: true, color: C.ice, charSpacing: 1.2,
  });
  text(s, "$5,000", {
    x: M + 0.42, y: 2.5, w: 3.5, h: 1.0,
    fontFace: F.head, fontSize: 62, bold: true, color: "FFFFFF",
  });
  text(
    s,
    "granted to one agent, for one vendor category, under the city's $10,000 informal-quote threshold.",
    {
      x: M + 0.42, y: 3.6, w: 3.5, h: 1.0,
      fontFace: F.body, fontSize: 13.5, color: C.ice, lineSpacing: 20,
    }
  );
  s.addShape(pres.ShapeType.line, {
    x: M + 0.42, y: 4.62, w: 3.5, h: 0,
    line: { color: "3A4479", width: 1 },
  });
  text(s, "Set by a human. Enforced before the call.", {
    x: M + 0.42, y: 4.76, w: 3.5, h: 0.34,
    fontFace: F.body, fontSize: 13, italic: true, color: "FFFFFF",
  });

  // Right: four decisions
  const rx = M + 4.75, rw = CW - 4.75;
  text(s, "FOUR REQUESTS, FOUR SIGNED DECISIONS", {
    x: rx, y: 1.9, w: rw, h: 0.28,
    fontFace: F.mono, fontSize: 10, bold: true, color: C.mutedLight, charSpacing: 1.2,
  });

  const decisions = [
    ["01", "$2,400", "ALLOWED", "$2,600 remaining", true],
    ["02", "$1,350", "ALLOWED", "$1,250 remaining", true],
    ["03", "$1,100", "ALLOWED", "$150 remaining", true],
    ["04", "$900", "BLOCKED", "over delegated limit", false],
  ];

  decisions.forEach(([n, amt, verdict, note, ok], i) => {
    const ry = 2.3 + i * 0.78;
    s.addShape(pres.ShapeType.roundRect, {
      x: rx, y: ry, w: rw, h: 0.66, rectRadius: 0.05,
      fill: { color: ok ? C.card : C.denyBg },
      line: { color: ok ? C.cardEdge : "EFCBCE", width: 1 },
      shadow: softShadow(),
    });
    text(s, n, {
      x: rx + 0.3, y: ry, w: 0.4, h: 0.66,
      fontFace: F.mono, fontSize: 12, bold: true,
      color: ok ? C.mutedLight : C.deny, valign: "middle",
    });
    text(s, amt, {
      x: rx + 0.85, y: ry, w: 1.2, h: 0.66,
      fontFace: F.mono, fontSize: 15, bold: true,
      color: ok ? C.navy : C.deny, valign: "middle",
    });
    // verdict pill
    s.addShape(pres.ShapeType.roundRect, {
      x: rx + 2.2, y: ry + 0.15, w: 1.32, h: 0.36, rectRadius: 0.06,
      fill: { color: ok ? C.allowBg : "F5D6D8" },
      line: { color: ok ? "BFE3CE" : "E7B4B8", width: 1 },
    });
    text(s, verdict, {
      x: rx + 2.2, y: ry + 0.15, w: 1.32, h: 0.36,
      fontFace: F.mono, fontSize: 10.5, bold: true,
      color: ok ? C.allow : C.deny, align: "center", valign: "middle",
    });
    text(s, note, {
      x: rx + 3.75, y: ry, w: rw - 4.05, h: 0.66,
      fontFace: F.body, fontSize: 13, color: ok ? C.mutedLight : C.deny, valign: "middle",
    });
  });

  text(
    s,
    "Every request carries the agent identity, the policy result, the remaining authority, and a signed OCSF record.",
    {
      x: rx, y: 5.48, w: rw, h: 0.4,
      fontFace: F.body, fontSize: 12.5, color: C.mutedLight,
    }
  );

  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 5.5, w: 4.35, h: 0.82, rectRadius: 0.05,
    fill: { color: C.denyBg }, line: { color: "EFCBCE", width: 1 },
  });
  text(s, "The denial is evidence too.", {
    x: M + 0.32, y: 5.5, w: 3.7, h: 0.82,
    fontFace: F.head, fontSize: 15, bold: true, color: C.deny, valign: "middle",
  });

  footer(s, 4);
  s.addNotes(
    "1:45–3:00 — Your longest beat; this is the slide people repeat afterward. " +
      "Read the four rows out loud, then stop on 04: the request fails closed, and the refusal is itself a signed, " +
      "chained record. Most systems log what happened; this one proves what was refused."
  );
}

/* =================================================================== *
 * 05 — Where it applies + how it deploys (light)
 * =================================================================== */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  lightHead(
    s,
    "One control layer, three city workflows",
    "Horizontal by design — the first wedge is the public institution, not the AI startup."
  );

  const uses = [
    {
      n: "01",
      t: "Fiscal controls",
      d: "Set spending ceilings and approval boundaries before a procurement agent can act, not in the reconciliation afterward.",
    },
    {
      n: "02",
      t: "Resident-data access",
      d: "Attribute every sensitive lookup to a specific agent and to the human authority that delegated it.",
    },
    {
      n: "03",
      t: "Incident review",
      d: "Give investigators a portable record they can verify without relying on the live vendor service.",
    },
  ];

  const cw = 3.86, gap = 0.42, cy = 1.86, ch = 2.62;
  uses.forEach((u, i) => {
    const cx = M + i * (cw + gap);
    s.addShape(pres.ShapeType.roundRect, {
      x: cx, y: cy, w: cw, h: ch, rectRadius: 0.05,
      fill: { color: C.card }, line: { color: C.cardEdge, width: 1 },
      shadow: softShadow(),
    });
    chip(s, u.n, cx + 0.34, cy + 0.34);
    text(s, u.t, {
      x: cx + 0.34, y: cy + 0.96, w: cw - 0.68, h: 0.4,
      fontFace: F.head, fontSize: 20, bold: true, color: C.navy,
    });
    text(s, u.d, {
      x: cx + 0.34, y: cy + 1.46, w: cw - 0.68, h: 1.0,
      fontFace: F.body, fontSize: 13, color: C.mutedLight, lineSpacing: 19,
    });
  });

  // Deployment / procurement path
  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 4.82, w: CW, h: 1.5, rectRadius: 0.05,
    fill: { color: "E9EEF8" }, line: { color: "D5DEEE", width: 1 },
  });
  text(s, "How it deploys", {
    x: M + 0.42, y: 5.06, w: 2.9, h: 0.34,
    fontFace: F.head, fontSize: 17, bold: true, color: C.navy,
  });
  text(s, "Answers the first three questions procurement asks.", {
    x: M + 0.42, y: 5.44, w: 2.5, h: 0.7,
    fontFace: F.body, fontSize: 12.5, color: C.mutedLight, lineSpacing: 18,
  });

  const deploy = [
    ["In the city's environment.", "Container or managed service — evidence stays inside the city's boundary."],
    ["Verification is offline.", "The MIT-licensed verifier checks records without calling AI Identity."],
    ["No data retention.", "The gateway sees the request envelope, not the resident record behind it."],
  ];
  deploy.forEach(([h, d], i) => {
    const dx = M + 3.55 + i * 2.82;
    text(s, h, {
      x: dx, y: 5.06, w: 2.62, h: 0.32,
      fontFace: F.body, fontSize: 13, bold: true, color: C.navy,
    });
    text(s, d, {
      x: dx, y: 5.42, w: 2.62, h: 0.74,
      fontFace: F.body, fontSize: 11.5, color: C.mutedLight, lineSpacing: 16,
    });
  });

  footer(s, 5);
  s.addNotes(
    "3:00–3:30 — Name the three workflows quickly; do not read the cards. " +
      "Spend the time on the bottom band — it pre-empts the security review, the data-residency question, " +
      "and 'what happens if you go out of business.'"
  );
}

/* =================================================================== *
 * 06 — The moat: OCSF + verifiable evidence (light)
 * =================================================================== */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  lightHead(
    s,
    "The proof already exists",
    "Working software and a vendor-neutral evidence model — not a roadmap slide."
  );

  // Left: OCSF credential
  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 1.86, w: 5.3, h: 3.3, rectRadius: 0.05,
    fill: { color: C.card }, line: { color: C.cardEdge, width: 1 },
    shadow: softShadow(),
  });
  text(s, "OCSF 1.9", {
    x: M + 0.42, y: 2.16, w: 4.5, h: 0.82,
    fontFace: F.head, fontSize: 46, bold: true, color: C.navy,
  });
  text(
    s,
    "Our founder authored the contribution that added the attestation object and the record_integrity profile to the Open Cybersecurity Schema Framework.",
    {
      x: M + 0.42, y: 3.06, w: 4.46, h: 1.1,
      fontFace: F.body, fontSize: 13.5, color: C.mutedLight, lineSpacing: 20,
    }
  );
  s.addShape(pres.ShapeType.line, {
    x: M + 0.42, y: 4.3, w: 4.46, h: 0,
    line: { color: C.cardEdge, width: 1 },
  });
  text(s, "It is the log schema your SIEM already speaks.", {
    x: M + 0.42, y: 4.46, w: 4.46, h: 0.5,
    fontFace: F.head, fontSize: 15, italic: true, color: C.navy,
  });

  // Right: what ships today
  const rx = M + 5.72, rw = CW - 5.72;
  text(s, "SHIPPING TODAY", {
    x: rx, y: 1.9, w: rw, h: 0.28,
    fontFace: F.mono, fontSize: 10, bold: true, color: C.mutedLight, charSpacing: 1.2,
  });

  const proof = [
    "Emits the merged OCSF shape — no proprietary log format.",
    "Signed checkpoints anchor Merkle-batched audit records.",
    "An MIT-licensed verifier checks the evidence offline.",
    "A public checkpoint feed supports independent review.",
  ];
  proof.forEach((p, i) => {
    const py = 2.34 + i * 0.72;
    s.addShape(pres.ShapeType.roundRect, {
      x: rx, y: py, w: rw, h: 0.6, rectRadius: 0.05,
      fill: { color: C.card }, line: { color: C.cardEdge, width: 1 },
      shadow: softShadow(),
    });
    s.addShape(pres.ShapeType.ellipse, {
      x: rx + 0.28, y: py + 0.19, w: 0.22, h: 0.22,
      fill: { color: C.allow }, line: { color: C.allow, width: 0 },
    });
    text(s, p, {
      x: rx + 0.72, y: py, w: rw - 1.0, h: 0.6,
      fontFace: F.body, fontSize: 13, color: C.navy, valign: "middle",
    });
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 5.4, w: CW, h: 0.92, rectRadius: 0.05,
    fill: { color: C.navy }, line: { color: C.navy, width: 0 },
  });
  text(
    s,
    "Vendor-neutral by construction: verifying a city's evidence does not require trusting AI Identity — or AI Identity still existing.",
    {
      x: M + 0.42, y: 5.4, w: CW - 0.84, h: 0.92,
      fontFace: F.head, fontSize: 16, color: "FFFFFF", valign: "middle",
    }
  );

  footer(s, 6);
  s.addNotes(
    "3:30–4:15 — This is the slide that separates you from seven other 'AI for cities' pitches. " +
      "Say the OCSF line plainly and once — it is checkable, so do not oversell it. " +
      "The navy band is the answer to 'won't our existing vendor just add this?'"
  );
}

/* =================================================================== *
 * 07 — The ask (light)
 * =================================================================== */
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  lightHead(
    s,
    "What we're asking Colorado for",
    "One bounded workflow, one technical owner, one verifiable result."
  );

  // One wide card: the pilot request, stated in three constraints
  const cx = M, cy = 1.86, cw = CW, ch = 3.34;
  s.addShape(pres.ShapeType.roundRect, {
    x: cx, y: cy, w: cw, h: ch, rectRadius: 0.05,
    fill: { color: C.card }, line: { color: C.cardEdge, width: 1 },
    shadow: softShadow(),
  });

  text(s, "PILOT REQUEST", {
    x: cx + 0.42, y: cy + 0.3, w: 5.2, h: 0.28,
    fontFace: F.mono, fontSize: 10, bold: true, color: C.iceDeep, charSpacing: 1.2,
  });
  text(s, "One city workflow, end to end", {
    x: cx + 0.42, y: cy + 0.66, w: 8.0, h: 0.46,
    fontFace: F.head, fontSize: 25, bold: true, color: C.navy,
  });

  const terms = [
    ["01", "Scope", "A single agent workflow with a real spending or data boundary."],
    ["02", "People", "One technical owner on the city side. No procurement cycle to start."],
    ["03", "Result", "Agent identity, enforced policy, and evidence a third party can verify."],
  ];
  const colw = 3.33, pitch = 3.83;
  terms.forEach(([n, label, body], i) => {
    const tx = cx + 0.42 + i * pitch;
    chip(s, n, tx, cy + 1.4);
    text(s, label, {
      x: tx, y: cy + 2.0, w: colw, h: 0.36,
      fontFace: F.head, fontSize: 19, bold: true, color: C.navy,
    });
    text(s, body, {
      x: tx, y: cy + 2.46, w: colw, h: 0.72,
      fontFace: F.body, fontSize: 13, color: C.mutedLight, lineSpacing: 19,
    });
  });

  // Status strip
  const stats = [
    ["Boulder, Colorado", "Built here"],
    ["Bootstrapped pre-seed", "No outside capital"],
    ["Working software", "Not a prototype"],
  ];
  stats.forEach(([h, d], i) => {
    const sx = M + i * 4.2;
    text(s, h, {
      x: sx, y: 5.56, w: 3.9, h: 0.3,
      fontFace: F.head, fontSize: 16, bold: true, color: C.navy,
    });
    text(s, d, {
      x: sx, y: 5.9, w: 3.9, h: 0.3,
      fontFace: F.body, fontSize: 12.5, color: C.mutedLight,
    });
  });

  footer(s, 7);
  s.addNotes(
    "4:15–4:40 — The ask, said once and plainly; do not soften it into 'we would love to explore.' " +
      "Name the three constraints and stop. If someone asks whether a city is already using this, answer straight — " +
      "the deck claims nothing either way. Decide in advance how you answer 'are you raising?'"
  );
}

/* =================================================================== *
 * 08 — Founder + close (dark)
 * =================================================================== */
{
  const s = pres.addSlide();
  s.background = { color: C.ink };

  text(s, "Jeff Leva", {
    x: M, y: 1.72, w: 7.0, h: 0.7,
    fontFace: F.head, fontSize: 40, bold: true, color: "FFFFFF",
  });
  text(s, "Founder & CEO", {
    x: M, y: 2.48, w: 7.0, h: 0.36,
    fontFace: F.mono, fontSize: 13, color: C.iceDeep, charSpacing: 1.2,
  });
  text(
    s,
    "Twelve years operating production systems where reliability and accountability matter, including cloud banking infrastructure supporting more than $50 billion in client assets.",
    {
      x: M, y: 3.12, w: 6.6, h: 1.2,
      fontFace: F.body, fontSize: 15, color: C.mutedDark, lineSpacing: 24,
    }
  );

  s.addShape(pres.ShapeType.line, {
    x: M, y: 4.62, w: 6.6, h: 0,
    line: { color: C.inkLine, width: 1 },
  });
  text(s, "jeff@ai-identity.co", {
    x: M, y: 4.86, w: 3.4, h: 0.34,
    fontFace: F.mono, fontSize: 15, color: "FFFFFF",
  });
  text(s, "www.ai-identity.co", {
    x: M, y: 5.3, w: 3.4, h: 0.34,
    fontFace: F.mono, fontSize: 15, color: "FFFFFF",
  });

  // Closing panel
  const px = 8.15, py = 1.68, pw = 4.43, ph = 4.34;
  s.addShape(pres.ShapeType.roundRect, {
    x: px, y: py, w: pw, h: ph, rectRadius: 0.06,
    fill: { color: C.inkPanel }, line: { color: C.inkLine, width: 1 },
  });
  text(s, "IF YOU REMEMBER ONE THING", {
    x: px + 0.4, y: py + 0.4, w: pw - 0.8, h: 0.28,
    fontFace: F.mono, fontSize: 9.5, bold: true, color: C.iceDeep, charSpacing: 1.2,
  });
  text(
    s,
    "Cities are about to delegate real authority to software agents.",
    {
      x: px + 0.4, y: py + 0.9, w: pw - 0.8, h: 1.3,
      fontFace: F.head, fontSize: 22, color: "FFFFFF", lineSpacing: 30,
    }
  );
  text(
    s,
    "The accountability layer has to exist before the delegation does — and the evidence has to outlive the vendor that produced it.",
    {
      x: px + 0.4, y: py + 2.16, w: pw - 0.8, h: 1.2,
      fontFace: F.body, fontSize: 14, color: C.mutedDark, lineSpacing: 21,
    }
  );
  s.addShape(pres.ShapeType.line, {
    x: px + 0.4, y: py + 3.68, w: pw - 0.8, h: 0,
    line: { color: C.inkLine, width: 1 },
  });
  text(s, "One workflow. One owner.", {
    x: px + 0.4, y: py + 3.84, w: pw - 0.8, h: 0.34,
    fontFace: F.mono, fontSize: 12, color: "4FD18B",
  });

  footerDark(s, 8);
  s.addNotes(
    "4:40–5:00 — Close on the panel, not the bio. Two sentences, then stop talking. " +
      "Consider naming the bank or platform in the bio line if you are permitted to — an unattributed $50B reads as padding to investors in the room."
  );
}

pres
  .writeFile({ fileName: "AI-Identity-DenAI-Showcase-2026-v4.pptx" })
  .then((f) => console.log("wrote", f));
