import { MongoClient, type Db } from "mongodb";

/**
 * Serverless-safe MongoDB client.
 *
 * Each Vercel function invocation may run in a fresh isolate, but isolates
 * can be reused (warm starts). Caching the client on globalThis means we
 * reuse the connection pool across warm invocations without leaking
 * connections on the cold start path.
 *
 * Used by /api/probe-signup to persist signups for the daily summary cron.
 * Insert path is best-effort — if the Mongo write fails for any reason, the
 * route still returns the user-facing 200/202 because the Resend email and
 * Vercel Analytics event have already fired.
 */

const DB_NAME = "ai_identity_probes";

declare global {
  var __probeSignupMongoClient: MongoClient | undefined;
}

export async function getProbeDb(): Promise<Db | null> {
  const uri = process.env.MONGODB_URI;
  if (!uri) return null;

  if (!globalThis.__probeSignupMongoClient) {
    globalThis.__probeSignupMongoClient = new MongoClient(uri, {
      // Conservative timeouts — we never want a flaky Mongo to stall the
      // user-facing request. The route's caller catches and continues.
      serverSelectionTimeoutMS: 3000,
      connectTimeoutMS: 3000,
      socketTimeoutMS: 5000,
    });
    await globalThis.__probeSignupMongoClient.connect();
  }
  return globalThis.__probeSignupMongoClient.db(DB_NAME);
}
