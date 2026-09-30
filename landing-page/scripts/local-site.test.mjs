import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { once } from "node:events";
import { test } from "node:test";
import { createLocalServices } from "./local-services.mjs";

async function unusedPort() {
  const server = createServer();
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const port = server.address().port;
  server.close();
  await once(server, "close");
  return port;
}

async function post(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(15_000),
  });
  return { status: response.status, body: await response.json() };
}

test("website routes use local services without cloud credentials", { timeout: 120_000 }, async () => {
  const { server, messages } = createLocalServices();
  server.listen(4020, "127.0.0.1");
  await once(server, "listening");

  let site;
  try {
    const port = await unusedPort();
    const base = `http://127.0.0.1:${port}`;
    let output = "";
    site = spawn(process.execPath, ["node_modules/next/dist/bin/next", "dev", "-H", "127.0.0.1", "-p", String(port)], {
      cwd: new URL("..", import.meta.url),
      env: {
        ...process.env,
        NEXT_TELEMETRY_DISABLED: "1",
        LOCAL_SERVICES: "1",
        RESEND_API_KEY: "re_local_only",
        RESEND_BASE_URL: "http://127.0.0.1:4020",
        MONGODB_URI: "",
        VERTEX_PROJECT_ID: "",
      },
      stdio: ["ignore", "pipe", "pipe"],
    });
    for (const stream of [site.stdout, site.stderr]) {
      stream.on("data", (chunk) => {
        output = (output + chunk.toString()).slice(-4000);
      });
    }

    const deadline = Date.now() + 90_000;
    let chat;
    while (Date.now() < deadline) {
      if (site.exitCode !== null) {
        assert.fail(`Next.js exited early:\n${output}`);
      }
      try {
        chat = await post(`${base}/api/forensics/ask`, { query: "Audit chains?" });
        if (chat.status === 200) break;
        assert.fail(`Forensics route returned ${chat.status}: ${JSON.stringify(chat.body)}\n${output}`);
      } catch (error) {
        if (error.code === "ERR_ASSERTION") throw error;
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    }
    assert.ok(chat, `Next.js did not start:\n${output}`);
    assert.equal(chat.status, 200, output);
    assert.match(chat.body.answer, /No documents were searched/);
    assert.deepEqual(chat.body.citations, []);

    const signup = await post(`${base}/api/probe-signup`, {
      email: "signup@example.test",
      probe: "newsletter",
      source: "local-test",
    });
    assert.equal(signup.status, 200, JSON.stringify(signup.body));
    assert.equal(signup.body.delivered, true);

    const request = await post(`${base}/api/service-request`, {
      name: "Local Test",
      email: "request@example.test",
      company: "Example",
      service: "intro-call",
      description: "Local service smoke test",
      paidAcknowledged: true,
    });
    assert.equal(request.status, 200, JSON.stringify(request.body));
    assert.equal(request.body.delivered, true);

    assert.equal(messages.length, 2);
    assert.match(messages[0].subject, /newsletter/);
    assert.match(messages[1].subject, /Service request/);
    assert.equal(messages[0].reply_to, "signup@example.test");
    assert.equal(messages[1].reply_to, "request@example.test");
  } finally {
    if (site && site.exitCode === null) {
      site.kill("SIGTERM");
      await once(site, "exit");
    }
    server.close();
    await once(server, "close");
  }
});
