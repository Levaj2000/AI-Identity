import { NextRequest, NextResponse } from "next/server";
import { GoogleAuth } from "google-auth-library";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const PROJECT_ID = process.env.VERTEX_PROJECT_ID;
const LOCATION = process.env.VERTEX_LOCATION ?? "us";
const ENGINE_ID = process.env.VERTEX_ENGINE_ID ?? "forensics-agent";
const SERVING_CONFIG = "default_serving_config";

const PREAMBLE = `You are the AI Identity Forensics Assistant.
Answer questions ONLY using information from the provided sources about AI agent identity, forensics, audit chains, attestations, and compliance.
If the sources do not contain enough information to answer, say plainly: "I don't have that in our forensics docs — try asking about agent identity, audit chains, attestations, or compliance."
Never invent product features, pricing, customers, or company facts.
Be concise: 1-3 short paragraphs. Cite every claim.`;

const MAX_QUERY_LENGTH = 500;

let cachedAuth: GoogleAuth | null = null;

function getAuth(): GoogleAuth {
  if (cachedAuth) return cachedAuth;
  const scopes = ["https://www.googleapis.com/auth/cloud-platform"];
  const credentialsJson = process.env.GOOGLE_SERVICE_ACCOUNT_JSON;
  if (credentialsJson) {
    cachedAuth = new GoogleAuth({
      credentials: JSON.parse(credentialsJson),
      scopes,
    });
  } else {
    cachedAuth = new GoogleAuth({ scopes });
  }
  return cachedAuth;
}

async function getAccessToken(): Promise<string> {
  const auth = getAuth();
  const client = await auth.getClient();
  const tokenResponse = await client.getAccessToken();
  const token =
    typeof tokenResponse === "string" ? tokenResponse : tokenResponse?.token;
  if (!token) throw new Error("Failed to acquire access token");
  return token;
}

interface AnswerReference {
  chunkInfo?: {
    content?: string;
    documentMetadata?: {
      title?: string;
      uri?: string;
      structData?: { source_url?: string; title?: string };
    };
  };
}

interface AnswerResponse {
  answer?: {
    answerText?: string;
    references?: AnswerReference[];
    state?: string;
  };
  session?: { name?: string };
}

export async function POST(req: NextRequest) {
  if (!PROJECT_ID) {
    return NextResponse.json(
      { error: "Forensics agent is not configured" },
      { status: 503 },
    );
  }

  let body: { query?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const query = typeof body.query === "string" ? body.query.trim() : "";
  if (!query) {
    return NextResponse.json({ error: "Missing query" }, { status: 400 });
  }
  if (query.length > MAX_QUERY_LENGTH) {
    return NextResponse.json(
      { error: `Query too long (max ${MAX_QUERY_LENGTH} characters)` },
      { status: 400 },
    );
  }

  let accessToken: string;
  try {
    accessToken = await getAccessToken();
  } catch (err) {
    console.error("Auth error:", err);
    return NextResponse.json(
      { error: "Forensics agent auth failed" },
      { status: 503 },
    );
  }

  const url =
    `https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}` +
    `/locations/${LOCATION}/collections/default_collection/engines/${ENGINE_ID}` +
    `/servingConfigs/${SERVING_CONFIG}:answer`;

  const payload = {
    query: { text: query },
    answerGenerationSpec: {
      modelSpec: { modelVersion: "stable" },
      promptSpec: { preamble: PREAMBLE },
      includeCitations: true,
      ignoreAdversarialQuery: true,
      ignoreNonAnswerSeekingQuery: false,
      ignoreLowRelevantContent: true,
      answerLanguageCode: "en",
    },
    relatedQuestionsSpec: { enable: false },
    safetySpec: { enable: true },
  };

  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      "X-Goog-User-Project": PROJECT_ID,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    console.error("Vertex AI Search error:", response.status, errorText);
    return NextResponse.json(
      { error: "Search service error" },
      { status: 502 },
    );
  }

  const data = (await response.json()) as AnswerResponse;

  const seen = new Set<string>();
  const citations = (data.answer?.references ?? [])
    .map((ref) => {
      const meta = ref.chunkInfo?.documentMetadata;
      const title = meta?.structData?.title ?? meta?.title ?? "Source";
      const url = meta?.structData?.source_url ?? null;
      return { title, url };
    })
    .filter((c) => {
      const key = `${c.title}|${c.url ?? ""}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

  return NextResponse.json({
    answer: data.answer?.answerText ?? "",
    citations,
    state: data.answer?.state ?? null,
  });
}
