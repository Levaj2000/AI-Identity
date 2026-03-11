# AI Identity

[![CI](https://github.com/Levaj2000/AI-Identity/actions/workflows/ci.yml/badge.svg)](https://github.com/Levaj2000/AI-Identity/actions/workflows/ci.yml)

**Identity, permissions, and guardrails for AI agents.**

AI Identity is an API proxy and dashboard that sits between AI agents and external APIs. Each agent gets its own identity, permissions, and guardrails — the Okta for AI agents.

## Architecture

```
ai-identity/
├── api/          # FastAPI API server — identity service, admin API (port 8001)
├── gateway/      # FastAPI proxy gateway — request routing & policy enforcement (port 8002)
├── common/       # Shared code — DB models, auth, config, schemas
├── dashboard/    # React + TypeScript + Tailwind — agent management UI
├── scripts/      # Dev scripts — seed data, migrations
└── pyproject.toml
```

### Components

1. **Identity Service** (`api/`) — Agent CRUD, API key issuance (`aid_sk_` prefix), key rotation, capabilities management
2. **Proxy Gateway** (`gateway/`) — Authenticates agent keys, evaluates policies, forwards or blocks requests, logs decisions
3. **Shared Library** (`common/`) — SQLAlchemy models, Pydantic schemas, auth utilities, config — imported by both api/ and gateway/
4. **Dashboard** (`dashboard/`) — React SPA for agent management, policy editor, live traffic feed, spend charts

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (or use the Docker setup)

### Local Development

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r api/requirements.txt
pip install -r gateway/requirements.txt
pip install -e common/

# 3. Copy environment variables
cp .env.example .env
# Edit .env with your database URL and secrets

# 4. Start the API server (port 8001)
uvicorn api.app.main:app --reload --port 8001

# 5. Start the gateway (port 8002) — in a separate terminal
uvicorn gateway.app.main:app --reload --port 8002

# 6. Start the dashboard
cd dashboard && npm install && npm run dev
```

### Running Tests

```bash
# All tests
pytest

# API tests only
pytest api/tests/

# Gateway tests only
pytest gateway/tests/
```

## API Keys

Agent API keys use the `aid_sk_` prefix with SHA-256 hashed storage and a show-once pattern. Keys are only displayed once at creation time.

Key rotation supports a 24-hour grace period — both old and new keys work during the transition.

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL (Neon)
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS
- **Deployment**: Render (API + Gateway), Vercel (Dashboard)

## License

Proprietary — All rights reserved.
