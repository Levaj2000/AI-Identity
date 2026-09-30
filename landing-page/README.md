# Local website services

The public site uses MongoDB for best-effort probe-signup storage, Resend for
probe and service-request emails, and Vertex AI Search for the forensics chat.
The API server used by the SDKs is **not** in this repository. The steps below
run the website without cloud accounts or sending real email. The mock chat
exercises the request/response path, but does not retrieve documents or
generate real answers.

Prerequisites: Node.js 20+, npm, and Docker with the Compose plugin for MongoDB.
The site and mock server run on the host, not inside Compose.

From the repository root, start MongoDB (in its own terminal):

```sh
docker compose up -d --wait mongo
```

In a second terminal, start the local email and search service:

```sh
cd landing-page
npm ci
npm run local-services
```

In a third terminal, configure and start the site:

```sh
cd landing-page
cp .env.local.example .env.local
npm run dev -- -H 127.0.0.1
```

The example config points MongoDB and the Resend SDK at loopback. `LOCAL_SERVICES=1`
routes the forensics API to the local search response only in Next.js development
mode; no Google credentials or project ID are needed. The mock server binds to
`127.0.0.1:4020`, stores outgoing emails in memory only, and makes no outbound
requests. It resets when restarted. Compose publishes MongoDB to
`127.0.0.1:27017` only, with a persistent local volume and **no authentication**.
Do not expose either service on a public interface or put real user data in them.

## Verify the path

Use disposable data. From another terminal:

```sh
curl -fsS http://127.0.0.1:4020/health
curl -fsS -X POST http://127.0.0.1:3000/api/probe-signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"local@example.test","probe":"newsletter","source":"local-smoke"}'
curl -fsS http://127.0.0.1:4020/__messages
docker compose exec -T mongo mongosh --quiet ai_identity_probes \
  --eval 'db.signups.countDocuments({source:"local-smoke"})'
curl -fsS -X POST http://127.0.0.1:3000/api/forensics/ask \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is an audit chain?"}'
```

The signup responds with `delivered: true`, one captured email appears in
`/__messages`, and the MongoDB count increases. The chat answer says it is a
local mock with no citations. You can exercise the service-request form the
same way; its emails also appear in `__messages`. If Docker is unavailable,
leave `MONGODB_URI` unset in `.env.local`: signup email still works but no
signup record is stored. MongoDB connection failures are best-effort and may
delay signup by a few seconds. If the mock server is stopped, emails are not
delivered; the routes return `delivered: false`.

To stop the services, stop both development processes and run
`docker compose down` from the repository root. The MongoDB volume remains;
`docker compose down -v` deletes local signup data.

## SDK smoke test

The same mock service serves one **read-only fixture** for the Python and
TypeScript SDKs: `GET /api/v1/agents` returns an empty paginated list. It
does not implement agent creation, authentication, policy enforcement, or any
other control-plane operation. Use only the disposable key shown below.
While `npm run local-services` is running, from the repository root:

```sh
PYTHONPATH=sdk/python/src python - <<'PY'
import asyncio
from ai_identity import AIIdentityClient

async def main():
    async with AIIdentityClient(
        api_key="aid_sk_local_only", base_url="http://127.0.0.1:4020"
    ) as client:
        agents = await client.agents.list()
        print(agents.total, agents.items)

asyncio.run(main())
PY
```

Install the Python SDK dependencies (`pip install -e ./sdk/python`) first.
`PYTHONPATH=sdk/python/src pytest sdk/python/tests -v` runs its offline
HTTP-path test without starting any service.
For TypeScript, run `npm ci && npm run build` inside `sdk/typescript`, then:

```sh
cd sdk/typescript
node --input-type=module -e 'import { AIIdentityClient } from "./dist/index.js"; const c = new AIIdentityClient({apiKey:"aid_sk_local_only",baseUrl:"http://127.0.0.1:4020"}); console.log(await c.agents.list())'
```

Both calls return an empty list; neither exercises the private API. Calls to
unsupported paths return 404 rather than a fabricated success response.

## Real service integration

To test real delivery or search, remove `LOCAL_SERVICES`, `RESEND_BASE_URL`,
and the dummy `RESEND_API_KEY` from `.env.local`. Set a real `RESEND_API_KEY`
and, for search, `VERTEX_PROJECT_ID`, `VERTEX_LOCATION`, and
`VERTEX_ENGINE_ID`. Authenticate locally with
`gcloud auth application-default login` and grant the account access to the
Vertex AI Search engine. These are external paid/credentialed services and
are **not** simulated faithfully by the local response. Never commit real
keys, credentials, or user submissions.

The SDKs use a configurable `base_url` (Python) or `baseUrl` (TypeScript).
Their production API is hosted separately, so Compose does not run it.
End-to-end SDK calls require access to the hosted API or a separately
provided compatible server. See `sdk/python/README.md` and
`sdk/typescript/README.md`.

Run `npm run test:local-services`, `npx tsc --noEmit`, and `npx next build`
to check the local service contract and site.
