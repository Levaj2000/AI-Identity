# Local Development Guide

This guide covers setting up and running the AI Identity stack on your local machine using Docker. It's intended for developers contributing to the project. For user-facing instructions, see [`QUICKSTART.md`](../QUICKSTART.md).

## Overview

The local development stack consists of three services managed by Docker Compose:

1. **`api`** — backend API server; agent management, policy storage, audit logging.
2. **`gateway`** — proxy service that enforces policies before routing requests.
3. **`db`** — PostgreSQL database for persistent data.

Requests from a client first hit the `gateway`, which queries the `api` to evaluate policies. If allowed, the `gateway` forwards the request. The `api` server is the only service that talks to the database.

```text
       Client
         │
         ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Gateway          │ ──▶ │ API Server       │ ──▶ │ Postgres         │
│ (localhost:8002) │     │ (localhost:8001) │     │ (localhost:5432) │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

## Prerequisites

- Docker and Docker Compose installed. See the [official Docker docs](https://docs.docker.com/get-docker/) for installation.
- Ports `5432`, `8001`, and `8002` must be free on your machine.

For runtime versions (Python, Postgres), refer to `Dockerfile.api`, `Dockerfile.gateway`, and `docker-compose.yml`. [`QUICKSTART.md`](../QUICKSTART.md) covers the user-facing onboarding flow; this doc is the contributor counterpart.

## First-time setup

Before launching the stack for the first time, generate a local `.env` with security keys:

```shell
make setup
```

This runs [`scripts/docker-setup.sh`](../scripts/docker-setup.sh), which:

1. Copies `.env.example` → `.env` if no `.env` exists.
2. Generates and populates secure values for `CREDENTIAL_ENCRYPTION_KEY`, `INTERNAL_SERVICE_KEY`, and `AUDIT_HMAC_KEY`.

One-time only. To regenerate keys, delete `.env` and re-run.

## Starting the stack

Build images and start all services in the background:

```shell
make up
```

The first run takes a few minutes to build images; subsequent starts are much faster. On startup the `api` service runs Alembic migrations automatically.

Verify all three containers are healthy:

```shell
make ps
```

Health endpoints are defined in [`api/app/main.py`](../api/app/main.py) and [`gateway/app/main.py`](../gateway/app/main.py):

```shell
curl http://localhost:8001/health
# {"status":"ok","version":"...","service":"ai-identity-api"}

curl http://localhost:8002/health
# {"status":"ok","version":"...","service":"ai-identity-gateway"}
```

## Viewing logs

Tail logs for `api` and `gateway` together:

```shell
make logs
```

For a single service, use Docker Compose directly:

```shell
docker compose logs -f api
```

Replace `api` with `gateway` or `db` as needed.

## Running migrations

Schema migrations are managed with Alembic; revision files live in `alembic/versions/`.

The `api` service runs `alembic upgrade head` automatically on startup. To run migrations manually against running services:

```shell
make migrate
```

This executes `alembic upgrade head` inside the running `api` container.

## Seeding test data

Populate the database with sample agents and keys:

```shell
make seed
```

This executes [`scripts/seed.py`](../scripts/seed.py) inside the `api` container. The script is idempotent and creates (if absent):

- A default user (`seed-dev@ai-identity.local`)
- Three sample agents: `ChatBot Alpha`, `Data Analyst`, `Image Creator`
- An active API key for each sample agent

### Seeding compliance data

Compliance framework data (e.g., NIST AI RMF, SOC 2) is seeded by a separate script — not wired into a `make` target. Run it manually inside the `api` container when you need it:

```shell
make shell-api
# inside the container:
python scripts/seed_compliance.py
```

## Common Makefile targets

| Target | What it does | When to use |
|---|---|---|
| `setup` | Generate `.env` with security keys | First-time setup, before `make up` |
| `up` | Build and start all services (detached) | Start the dev environment |
| `down` | Stop all services | Stop without removing volumes |
| `restart` | Restart all services | Apply changes that need a full restart |
| `logs` | Tail `api` + `gateway` logs | Debugging or live monitoring |
| `ps` | Show running containers | Health check / status |
| `shell-api` | Bash shell in the `api` container | Run scripts or inspect the API image |
| `shell-gw` | Bash shell in the `gateway` container | Run scripts or inspect the gateway image |
| `psql` | `psql` shell to the database | Inspect or hand-edit DB state |
| `migrate` | Run Alembic migrations | Apply schema changes manually |
| `seed` | Seed sample agents and keys | Populate dev data |
| `test` | Run pytest in API + gateway containers | Run backend test suites |
| `clean` | Stop services and remove all volumes | Full reset — deletes all data |

Run `make help` to see the full target list with descriptions.

## Troubleshooting

### Port conflicts

If another process is using `5432`, `8001`, or `8002`, Docker will fail to start the affected service. Either stop the conflicting process or change the host-side port mapping in `docker-compose.yml` (e.g. `"8001:8001"` → `"8003:8001"`).

### "Connection refused" on Postgres

The `api` service depends on `db` via `depends_on: condition: service_healthy` in `docker-compose.yml`, so it should not start until Postgres is accepting connections. If you still see connection errors — typically after the host machine has been suspended — `make restart` clears them.

### Full reset

If the database gets into a bad state, do a clean wipe. This **deletes the database volume** and all local data:

```shell
make clean
```

Then start fresh:

```shell
make up
make seed
```
