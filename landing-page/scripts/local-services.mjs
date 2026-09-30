import { createServer } from "node:http";
import { pathToFileURL } from "node:url";

const MAX_BODY_BYTES = 64 * 1024;

function respond(res, status, data) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

export function createLocalServices() {
  const messages = [];

  const server = createServer((req, res) => {
    if (req.method === "GET" && req.url === "/health") {
      respond(res, 200, { ok: true });
      return;
    }
    if (req.method === "GET" && req.url === "/__messages") {
      respond(res, 200, { messages });
      return;
    }
    const url = new URL(req.url, "http://127.0.0.1");
    if (req.method === "GET" && url.pathname === "/api/v1/agents") {
      const limit = Number(url.searchParams.get("limit") ?? 50);
      const offset = Number(url.searchParams.get("offset") ?? 0);
      if (
        !Number.isInteger(limit) ||
        limit < 0 ||
        !Number.isInteger(offset) ||
        offset < 0
      ) {
        respond(res, 400, { error: "invalid_pagination" });
        return;
      }
      respond(res, 200, { items: [], total: 0, limit, offset });
      return;
    }
    if (
      req.method !== "POST" ||
      (req.url !== "/emails" && req.url !== "/vertex/answer")
    ) {
      respond(res, 404, { error: "not_found" });
      return;
    }

    let body = "";
    let tooLarge = false;
    req.on("data", (chunk) => {
      if (tooLarge) return;
      body += chunk;
      if (Buffer.byteLength(body) > MAX_BODY_BYTES) {
        tooLarge = true;
        respond(res, 413, { error: "payload_too_large" });
      }
    });
    req.on("end", () => {
      if (tooLarge) return;
      let payload;
      try {
        payload = JSON.parse(body);
      } catch {
        respond(res, 400, { error: "invalid_json" });
        return;
      }

      if (req.url === "/emails") {
        if (
          typeof payload?.to !== "string" &&
          !Array.isArray(payload?.to)
        ) {
          respond(res, 400, { error: "missing_recipient" });
          return;
        }
        if (typeof payload.text !== "string") {
          respond(res, 400, { error: "missing_text" });
          return;
        }
        const id = `local-${messages.length + 1}`;
        messages.push({ id, ...payload });
        respond(res, 200, { id });
        return;
      }

      if (typeof payload?.query?.text !== "string") {
        respond(res, 400, { error: "missing_query" });
        return;
      }
      respond(res, 200, {
        answer: {
          answerText:
            "Local mock response only. No documents were searched. Configure Vertex AI Search to test real answers and citations.",
          references: [],
          state: "SUCCEEDED",
        },
      });
    });
  });

  return { server, messages };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const { server } = createLocalServices();
  server.listen(4020, "127.0.0.1", () => {
    console.log("Local email and search mocks listening on 127.0.0.1:4020");
    console.log("Captured emails: http://127.0.0.1:4020/__messages");
  });
}
