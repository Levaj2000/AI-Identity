import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { createLocalServices } from "./local-services.mjs";

const { server } = createLocalServices();
let base;

before(async () => {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});
after(() => new Promise((resolve) => server.close(resolve)));

test("captures email locally without sending it", async () => {
  const payload = {
    from: "sender@example.test",
    to: "recipient@example.test",
    subject: "Local test",
    text: "Hello from local development",
  };
  const response = await fetch(`${base}/emails`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { id: "local-1" });

  const messages = await fetch(`${base}/__messages`).then((res) => res.json());
  assert.deepEqual(messages.messages, [{ id: "local-1", ...payload }]);
});

test("search mock makes no factual or citation claims", async () => {
  const response = await fetch(`${base}/vertex/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: { text: "What is an audit chain?" } }),
  });
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.match(body.answer.answerText, /No documents were searched/);
  assert.deepEqual(body.answer.references, []);
});

test("SDK list fixture returns an empty paginated response", async () => {
  const response = await fetch(`${base}/api/v1/agents?limit=3&offset=2`, {
    headers: { "X-API-Key": "aid_sk_local_only" },
  });
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    items: [],
    total: 0,
    limit: 3,
    offset: 2,
  });
  const invalid = await fetch(`${base}/api/v1/agents?limit=-1`);
  assert.equal(invalid.status, 400);
});

test("invalid input and unknown routes do not record messages", async () => {
  const health = await fetch(`${base}/health`);
  assert.deepEqual(await health.json(), { ok: true });
  const badEmail = await fetch(`${base}/emails`, {
    method: "POST",
    body: JSON.stringify({ text: "No recipient" }),
  });
  assert.equal(badEmail.status, 400);
  const badSearch = await fetch(`${base}/vertex/answer`, {
    method: "POST",
    body: JSON.stringify({ query: {} }),
  });
  assert.equal(badSearch.status, 400);
  const unknown = await fetch(`${base}/other`);
  assert.equal(unknown.status, 404);
  const tooLarge = await fetch(`${base}/emails`, {
    method: "POST",
    body: "x".repeat(65 * 1024),
  });
  assert.equal(tooLarge.status, 413);
  const messages = await fetch(`${base}/__messages`).then((res) => res.json());
  assert.equal(messages.messages.length, 1);
});
