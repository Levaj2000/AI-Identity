<!--
This file was drafted by Ada herself on 2026-05-04 against her own runtime
code (serve.py, auth.py, ada/agent.py, ada/audit.py, Dockerfile). Every
read she made is captured as a signed entry in the AI Identity audit log
under agent_id=2e22d027-dd98-4096-a000-ddceb0e5d269. See the PR
description for the audit-log evidence. Lightly edited by a human to fix
markdown auto-link artifacts introduced by the chat shuttle; content and
citations are Ada's.
-->

# Ada — AI Identity's first dogfood agent

## What Ada is

Ada is an AI agent designed to act as a senior software engineer for the AI Identity team (`ada/agent.py:27`). Named after Ada Lovelace, her purpose is to assist with code reviews, bug investigations, architectural proposals, and maintaining code quality (`ada/agent.py:29-31`).

She is implemented as an ADK (Agent Development Kit) agent, defined in `ada/agent.py` (`ada/agent.py:122`), and powered by the `gemini-2.5-pro` model (`ada/agent.py:124`).

## Architecture

Ada's runtime is a FastAPI application served by `uvicorn` (`serve.py:17`, `serve.py:106`). The application is instantiated in `serve.py` and combines the core ADK API with a static UI and additional support endpoints (`serve.py:50-58`).

Key architectural points:

- The main application is created using `get_fast_api_app` from the Google ADK (`serve.py:21`, `serve.py:52`).
- It serves a web-based chat UI from a `.ui` directory (`serve.py:28`, `serve.py:78`).
- It provides `/healthz` and `/version` endpoints for monitoring and introspection (`serve.py:84-93`).
- The core agent logic (prompts, tool definitions) is in the `ada/` directory, while the server is at the repository root.

## Authentication model

Access to Ada can be protected by an authentication layer that verifies requests against the AI Identity platform.

- **Activation**: Authentication is enabled by setting the `ADA_REQUIRE_AUTH=1` environment variable (`auth.py:125`). It is disabled by default for local development (`serve.py:69-70`).
- **Mechanism**: When enabled, an ASGI middleware (`auth_middleware` in `serve.py:62`) intercepts incoming requests.
- **Verification**: Protected routes require an `X-Agent-Key` header (`auth.py:150`). This key is verified by making a POST request to the AI Identity `/api/v1/keys/verify` endpoint (`auth.py:78`).
- **Authorization**: The verification call itself is authenticated using an `ADA_ADMIN_KEY` (or `AI_IDENTITY_ADMIN_KEY`) passed as an `X-API-Key` header (`auth.py:34`, `auth.py:83`).
- **Failure mode**: If `ADA_REQUIRE_AUTH` is enabled but no admin key is configured, the server refuses requests to protected routes with a `503 Service Unavailable` rather than failing open (`auth.py:143-148`). Unauthenticated or invalid requests receive a `401 Unauthorized` (`auth.py:151-162`).
- **Public routes**: A set of routes — including the UI, documentation, and health checks — are explicitly public and do not require authentication (`auth.py:39-51`).

## Audit & policy flow (the dogfood hook)

The most critical integration with AI Identity is the audit and enforcement mechanism. Every tool call Ada attempts is subject to a policy check against the AI Identity Gateway, providing a real-time, observable demonstration of the platform's control over agent actions.

- **Activation**: The audit flow is enabled by setting `ADA_REQUIRE_AUDIT=1` (`ada/audit.py:84`). It is off by default to simplify local runs.
- **Hook**: Implemented as the ADK's `before_tool_callback` (`ada/agent.py:142`). Before any tool is executed, `before_tool_audit_callback` is invoked (`ada/audit.py:170`).
- **Enforcement call**: This function calls the AI Identity `/gateway/enforce` endpoint (`ada/audit.py:103`).
- **Request shape**: The request to the gateway includes Ada's `agent_id` and a synthetic endpoint representing the tool being used (e.g. `/ada/tools/read_file`) (`ada/audit.py:105-106`). Each request also contains a unique `X-Audit-Nonce` header for replay protection (`ada/audit.py:102`, `ada/audit.py:110`).
- **Decision**:
  - If the gateway responds with `"decision": "allow"`, the callback returns `None` and the ADK proceeds to execute the tool (`ada/audit.py:177`, `ada/audit.py:208`).
  - If the gateway responds with `"decision": "deny"`, the callback returns an error dictionary. The ADK stops execution and presents this error as the tool's output, effectively blocking the action (`ada/audit.py:199-206`).
  - If the gateway is unreachable or returns a 5xx, the tool call is also aborted with an explicit error message (`ada/audit.py:189-197`).

This synchronous, blocking check ensures Ada's ability to act is directly governed by policies managed in AI Identity (`ada/audit.py:15-17`).

## Tool surface

Ada's capabilities are defined by a set of read-only tools that allow her to inspect the codebase.

- `read_file(path)`
- `search_code(pattern, path_glob=None)`
- `list_repo_structure(path=".", max_depth=3)`
- `find_files(glob)`
- `git_log(path=None, max_count=20)`
- `git_blame(path, line)`
- `query_ai_identity_agent(agent_id)`

These tools are registered in `ada/agent.py` (`ada/agent.py:130-137`) and implemented in `ada/tools/`. All tools are strictly read-only to prevent unintended side effects (`ada/agent.py:58`).

## Configuration (env vars + secrets)

Ada's behavior is configured through environment variables.

**Auth & audit:**

- `ADA_REQUIRE_AUTH` — set to `1` to enable the authentication middleware.
- `ADA_ADMIN_KEY` / `AI_IDENTITY_ADMIN_KEY` — secret key for an admin/service account, used to authorize calls to the `/keys/verify` endpoint.
- `ADA_REQUIRE_AUDIT` — set to `1` to enable the pre-tool audit check with the AI Identity Gateway.
- `ADA_AGENT_ID` — the UUID for the Ada agent. Required for the audit hook.
- `AI_IDENTITY_API_KEY` — the runtime key for the Ada agent itself. Sent as `X-Agent-Key` in audit calls (`ada/audit.py:80`, `ada/audit.py:111-113`).

**API URLs:**

- `AI_IDENTITY_API_URL` — base URL for the AI Identity API (defaults to `https://api.ai-identity.co`) (`auth.py:33`).
- `AI_IDENTITY_GATEWAY_URL` — base URL for the AI Identity Gateway (defaults to `https://gateway.ai-identity.co`) (`ada/audit.py:72`).

**CORS & server:**

- `ADA_ALLOWED_ORIGINS` — comma-separated list of browser origins to allow for CORS (`auth.py:168-178`).
- `PORT` — port for the server to listen on. Respected by the `Dockerfile` and `serve.py` (`Dockerfile:54`).

**LLM:**

- `GOOGLE_GENAI_USE_VERTEXAI` — set to `1` in the production `Dockerfile` to use Vertex AI endpoints (`Dockerfile:48`).

## Runtime: local vs Cloud Run

Ada is designed to run both locally for development and as a containerized service in production.

**Local:**

- Run `python serve.py` from the repository root (`serve.py:5`).
- By default, auth and audit are **disabled** (`serve.py:70`, `ada/audit.py:184`). This allows for a frictionless local development experience without needing cloud credentials.
- The server runs on `127.0.0.1:8000` by default (`serve.py:100-101`).

**Cloud Run (via Dockerfile):**

- The `Dockerfile` defines the production image (`Dockerfile:1`).
- Based on `python:3.13-slim` and includes `git` and `ripgrep` for full tool functionality (`Dockerfile:13`, `Dockerfile:23-24`).
- By default, `ADA_REQUIRE_AUTH=1` and `ADA_REQUIRE_AUDIT=1` are set to **enabled** (`Dockerfile:44-45`), ensuring a secure-by-default deployment.
- The server binds to `0.0.0.0` and respects the `PORT` environment variable injected by Cloud Run (`Dockerfile:54`).
