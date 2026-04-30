# Ada — AI Identity's senior software engineer agent

Ada is built on Google's [Agent Development Kit (ADK)](https://adk.dev/) and
named after Ada Lovelace. She runs against `gemini-2.5-pro` via Vertex AI
(preferred — uses your Google for Startups Cloud Program credits) or Google
AI Studio (simpler for local testing).

She has four tools:

| Tool | Purpose |
|------|---------|
| `read_file(path)` | Read any file in the AI Identity repository. |
| `search_code(pattern, path_glob=None)` | Grep across the codebase. |
| `list_repo_structure(path=".")` | Tree-style directory listing. |
| `query_ai_identity_agent(agent_id)` | Call the AI Identity API for agent metadata — Ada's dogfood hook. |

The `query_ai_identity_agent` tool makes Ada the first agent to introspect
AI Identity itself. Once she's registered in the dashboard, her own API key
authenticates that call and she appears in her own audit trail. That is the
case-study moment.

## Local setup

```bash
# 1. Create a venv and install deps
cd agent
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Authenticate with Google Cloud (one-time)
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# 3. Configure Ada's environment
cp ada/.env.example ada/.env
# Edit ada/.env — fill GOOGLE_CLOUD_PROJECT and AI_IDENTITY_API_KEY

# 4. Run Ada in the terminal
adk run ada

# Or launch the inspector UI in a browser
adk web
```

## Registering Ada in AI Identity

To give Ada an identity (so the `query_ai_identity_agent` tool can return
her own record):

1. Go to `https://app.ai-identity.co` → Agents → New Agent.
2. Name: `ada`. Capabilities: `read`. Tier defaults are fine.
3. Copy the `aid_sk_…` key shown once.
4. Paste it into `agent/ada/.env` as `AI_IDENTITY_API_KEY`.
5. Note the agent UUID — that's the value to pass to `query_ai_identity_agent`.

## Antigravity deployment

Antigravity is Google's hosted runtime for ADK agents. Deployment is a
follow-up — see `docs/ada-deployment.md` (TODO) for the gcloud commands once
the GCS service account is provisioned.

For now, run Ada locally with `adk run ada` and use the web inspector to
debug tool calls.

## Project structure

```
agent/
├── requirements.txt
└── ada/
    ├── __init__.py
    ├── agent.py                 # root_agent definition + instruction
    ├── .env.example
    ├── README.md
    └── tools/
        ├── __init__.py
        ├── code_tools.py        # read_file, search_code, list_repo_structure
        └── ai_identity_tool.py  # query_ai_identity_agent
```

## Why Ada (not Bob v2)?

Bob v1.0 was sufficient for proving that the `.bob/rules-code/AGENTS.md`
training pattern works — six rounds of feedback measurably improved his
output. But the verification habit ("never claim tests pass without quoting
the pytest summary line") never fully internalized, and v1.0's rough edges
made him expensive to supervise on real product work.

Ada is the production replacement: ADK gives us full control over tools and
prompts, Vertex AI consumes our existing Google for Startups credits, and the
AI Identity integration turns every Ada session into a live case study.
