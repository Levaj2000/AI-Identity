# AI Identity

[![CI](https://github.com/Levaj2000/AI-Identity/actions/workflows/ci.yml/badge.svg)](https://github.com/Levaj2000/AI-Identity/actions/workflows/ci.yml)
[![PyPI - langchain-ai-identity](https://img.shields.io/pypi/v/langchain-ai-identity?label=langchain-ai-identity&color=blue)](https://pypi.org/project/langchain-ai-identity/)
[![License](https://img.shields.io/badge/license-proprietary-red)](LICENSE)

**Identity, governance, and forensic accountability for AI agents.**

AI Identity is the identity, governance, and forensic infrastructure that enterprises need to deploy AI agents with confidence. Each agent gets a cryptographic identity, enforceable policies, compliance-ready audit logs, and tamper-evident forensic trails.

| | URL |
|---|---|
| **Dashboard** | [ai-identity.co](https://ai-identity.co) |
| **API Docs** | [api.ai-identity.co/docs](https://api.ai-identity.co/docs) |

## Integrations

### LangChain

AI Identity provides a drop-in LangChain integration, available as a standalone PyPI package:

```bash
pip install langchain-ai-identity
```

```python
from langchain_ai_identity import create_ai_identity_agent

agent = create_ai_identity_agent(
    tools=[...],
    agent_id="<your-agent-uuid>",
    ai_identity_api_key="aid_sk_...",
    openai_api_key="sk-...",
)
result = agent.invoke({"input": "What is the latest news on AI safety?"})
```

Every LLM call is authenticated, policy-checked, and logged with a tamper-evident audit trail. See the [langchain-ai-identity PyPI page](https://pypi.org/project/langchain-ai-identity/) for full documentation.

### Offline Forensic Verification (CLI)

Auditors and incident responders can verify audit chain integrity offline — no network access or vendor trust required:

```bash
python3 cli/ai_identity_verify.py chain export.json
```

The CLI is a single-file, zero-dependency Python script that independently verifies HMAC-SHA256 hash chains exported from AI Identity.

## Architecture

```
ai-identity/
├── api/          # FastAPI API server — identity service, admin API (port 8001)
├── gateway/      # FastAPI proxy gateway — request routing & policy enforcement (port 8002)
├── common/       # Shared code — DB models, auth, config, schemas
├── dashboard/    # React + TypeScript + Tailwind — agent management UI
├── sdk/          # Client SDKs — Python, TypeScript, LangChain integration
├── cli/          # Offline forensic verification CLI
├── alembic/      # Database migrations
├── scripts/      # Dev scripts — seed data, migrations
└── pyproject.toml
```

### Components

1. **Identity Service** (`api/`) — Agent CRUD, API key issuance (`aid_sk_` prefix), key rotation, capabilities management
2. **Proxy Gateway** (`gateway/`) — Authenticates agent keys, evaluates policies, forwards or blocks requests, logs decisions
3. **Shared Library** (`common/`) — SQLAlchemy models, Pydantic schemas, auth utilities, config — imported by both api/ and gateway/
4. **Dashboard** (`dashboard/`) — React SPA for agent management, policy editor, live traffic feed, spend charts
5. **SDKs** (`sdk/`) — Python and TypeScript client libraries, plus the [LangChain integration](https://pypi.org/project/langchain-ai-identity/)
6. **Forensic CLI** (`cli/`) — Standalone offline audit chain verifier for DFIR and compliance

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/Levaj2000/AI-Identity.git
cd AI-Identity
make setup   # generates .env with security keys
make up      # builds and starts api + gateway + postgres
```

Services start at **localhost:8001** (API), **localhost:8002** (Gateway).

Run `make help` to see all available commands (migrate, seed, logs, shell, etc.).

### Manual Setup

**Prerequisites:** Python 3.11+, Node.js 18+, PostgreSQL

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
```

### Dashboard

```bash
cd dashboard
cp .env.example .env     # defaults to localhost:8001 API
npm install && npm run dev
```

The dashboard is deployed to [ai-identity.co](https://ai-identity.co) via Vercel. PR preview deploys are automatic.

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

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Alembic, Pydantic
- **Database**: PostgreSQL (Neon)
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS
- **Forensics**: HMAC-SHA256 hash-chained audit logs, offline CLI verifier
- **Integrations**: LangChain ([PyPI](https://pypi.org/project/langchain-ai-identity/))
- **CI/CD**: GitHub Actions, Ruff (lint + format), pytest (427+ tests)
- **Deployment**: GKE Autopilot (API + Gateway), Vercel (Dashboard), GitHub Actions CI/CD with Cloud Build

## License

Proprietary — All rights reserved.
