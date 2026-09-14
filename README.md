# AI Identity

[![CI](https://github.com/Levaj2000/AI-Identity/actions/workflows/ci.yml/badge.svg)](https://github.com/Levaj2000/AI-Identity/actions/workflows/ci.yml)
[![PyPI - langchain-ai-identity](https://img.shields.io/pypi/v/langchain-ai-identity?label=langchain-ai-identity&color=blue)](https://pypi.org/project/langchain-ai-identity/)
[![License](https://img.shields.io/badge/license-proprietary%20core%20·%20MIT%20verifier-blue)](LICENSE)

**Identity, governance, and forensic accountability for AI agents.**

Each agent gets a cryptographic identity, enforceable policies, compliance-ready audit logs, and tamper-evident forensic trails. The design constraint the whole system is built around: **trusting AI Identity evidence must never require trusting AI Identity.** Everything a relying party needs to check our records independently is openly licensed and runs offline.

## Verify our claims without asking us

The audit records are Merkle-batched and the signed checkpoints are published, so you can confirm the evidence is real before you talk to anyone here.

```bash
# 1. Pull a signed checkpoint from the public feed — no auth, no account
curl -s "https://api.ai-identity.co/evidence-anchor/checkpoints?limit=1"

# 2. Verify an exported audit chain offline — zero dependencies, MIT licensed
python3 cli/ai_identity_verify.py chain export.json

# 3. Verify a Merkle inclusion proof against a signed checkpoint
python3 cli/ai_identity_verify.py inclusion-proof bundle.json
```

The checkpoint history is also mirrored to the [`evidence-anchor-mirror`](https://github.com/Levaj2000/AI-Identity/tree/evidence-anchor-mirror) branch of this repo every six hours, with append-only enforcement — a rewritten batch, a vanished root, or a mutated envelope fails the run rather than overwriting the record. A checkpoint that verifies offline but is absent from the public feed is the tamper signal.

## Standards

The record formats are not ours to define, so we contributed them upstream:

- **OCSF** — the `attestation` object and `record_integrity` profile are merged into [OCSF 1.9](https://github.com/ocsf/ocsf-schema). This repo is the reference implementation that produced them; the emitter writes the merged shape.
- **CPEX** — the OCSF audit plugin is contributed to IBM's CPEX gateway under Apache-2.0.
- **CoSAI WS4** — the CMF ↔ OCSF cross-map and interop material lives in [`docs/cosai-ws4-ocsf-mapping/`](docs/cosai-ws4-ocsf-mapping/).

| | URL |
|---|---|
| **Website** | [ai-identity.co](https://ai-identity.co) |
| **API Docs** | [api.ai-identity.co/docs](https://api.ai-identity.co/docs) |
| **Checkpoint feed** | [api.ai-identity.co/evidence-anchor/checkpoints](https://api.ai-identity.co/evidence-anchor/checkpoints) |

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

## What is in this repository

```
AI-Identity/
+-- cli/            Offline verifier and audit review CLI (MIT)
+-- sdk/            Python, TypeScript, and LangChain SDKs
+-- integrations/   CPEX OCSF audit plugin (Apache-2.0), contributed upstream
+-- docs/           OCSF and CoSAI mappings, OTel crosswalk, evidence-anchor trust model, specs
+-- landing-page/   ai-identity.co (Next.js, deployed by Vercel)
+-- marketing/      Published collateral
+-- scripts/        Validators, the evidence-anchor mirror job, repo hygiene checks
```

### Where the platform lives

The control plane (API server, gateway, mandate service, dashboard, and deployment
manifests) moved to a private repository in September 2026. It is proprietary; see
[LICENSE](LICENSE). Nothing a relying party needs in order to verify AI Identity
evidence depends on it: the verifier, the record formats, and the checkpoint feed are
all here or upstream in OCSF. Commit history from before the split still contains the
platform source. That is deliberate: the repository was public so the code could be
audited, and history is part of that record.

### Running the verifier

```bash
python3 cli/ai_identity_verify.py chain export.json
python3 cli/ai_identity_verify.py inclusion-proof bundle.json
```

Chain verification is stdlib-only and runs on Python 3.9+. Signature checks on
attestations and checkpoints use the `cryptography` package. See [cli/README.md](cli/README.md).

### Running the tests

```bash
pip install -r requirements-dev.txt
pip install pytest httpx cryptography
ruff check . && ruff format --check .
pytest -v
```

## Tech Stack

- **Verifier**: Python 3.9+ standard library; `cryptography` for Ed25519 signature checks
- **SDKs**: Python 3.10+ (httpx, Pydantic), TypeScript, LangChain ([PyPI](https://pypi.org/project/langchain-ai-identity/))
- **CPEX plugin**: Rust
- **Record formats**: OCSF 1.9 `attestation` object and `record_integrity` profile, DSSE envelopes, Merkle-batched checkpoints
- **Site**: Next.js on Vercel
- **CI**: GitHub Actions, Ruff, pytest, CodeQL, OpenSSF Scorecard, evidence-anchor mirror every six hours

## Support and advisory

Bugs in the verifier, SDKs, or mapping documents go to GitHub issues. Help with your own system is a paid advisory engagement; request one at [ai-identity.co/request-services](https://www.ai-identity.co/request-services). See [SUPPORT.md](SUPPORT.md).

## License

**Platform: proprietary** — the API, gateway, dashboard, Mandate Service, and shared libraries are all rights reserved. The repository is public so the code can be audited, not reused.

**Verification and integration surfaces: permissive** — trusting AI Identity evidence must never require trusting AI Identity, so everything a relying party needs to verify our records independently is openly licensed:

| Component | License |
|---|---|
| [`cli/`](cli/) — offline verifier (ships in every Case File bundle) + audit review CLI | MIT |
| [`sdk/langchain/`](sdk/langchain/) — LangChain SDK ([PyPI](https://pypi.org/project/langchain-ai-identity/)) | MIT |
| CPEX OCSF audit plugin — contributed upstream to IBM's CPEX gateway | Apache-2.0 |

Record formats follow open standards: our schema contributions are merged upstream in [ocsf/ocsf-schema](https://github.com/ocsf/ocsf-schema) (OCSF 1.9). See [LICENSE](LICENSE) for the full terms.
