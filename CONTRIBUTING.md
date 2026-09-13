# Contributing to AI Identity

Thanks for your interest in contributing. This repository holds the public trust
surface of AI Identity: the offline verifier, the SDKs, the CPEX OCSF audit plugin,
and the OCSF, CoSAI, and OpenTelemetry mapping documents. The platform itself (API
server, gateway, mandate service, dashboard) is developed in a private repository
and is not open to contribution.

## Getting Started

1. **Fork the repository** and clone your fork locally
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

Prerequisites: Python 3.11+ for the tooling. The verifier CLI itself runs on 3.9+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install pytest httpx cryptography
```

The TypeScript SDK and the landing page each have their own `package.json`; run
`npm install` inside that directory when working on one of them. The CPEX plugin
in `integrations/cpex-ocsf-audit/` is a Rust crate with its own README.

## Running Tests

All tests must pass before submitting a PR:

```bash
pytest -v
```

That runs the verifier CLI suite in `cli/`. The chain verifier is stdlib-only;
the attestation and inclusion-proof tests need `cryptography`, and the `aid`
client tests need `httpx`.

## Code Style

We use **Ruff** for both linting and formatting. CI will reject PRs that don't pass these checks.

```bash
ruff check .            # lint
ruff check --fix .      # auto-fix
ruff format --check .   # formatting
ruff format .           # auto-format
```

## Submitting a Pull Request

1. **Open an issue first** describing the change you'd like to make
2. Wait for a maintainer to approve and assign the issue to you
3. Make your changes on a feature branch
4. Ensure all tests pass and code style checks are clean
5. Write a clear PR description linking to the issue (`Fixes #123`)
6. Submit the PR against `main`

### PR Checklist

- [ ] Tests pass locally (`pytest -v`)
- [ ] Linting passes (`ruff check .`)
- [ ] Formatting is clean (`ruff format --check .`)
- [ ] New behavior includes tests
- [ ] Changes to a record format or mapping document say which upstream standard they track

## Project Structure

| Directory | What Lives Here |
|-----------|----------------|
| `cli/` | Offline verifier and audit review CLI (MIT) |
| `sdk/` | Python, TypeScript, and LangChain SDKs |
| `integrations/` | CPEX OCSF audit plugin (Apache-2.0), contributed upstream |
| `docs/` | OCSF and CoSAI mappings, OTel crosswalk, evidence-anchor trust model, specs |
| `landing-page/` | ai-identity.co (Next.js, deployed by Vercel) |
| `marketing/` | Published collateral |
| `scripts/` | Validators, the evidence-anchor mirror job, repo hygiene checks |

## Where to Help

Check the [issues labeled `good first issue`](https://github.com/Levaj2000/AI-Identity/labels/good%20first%20issue) for tasks that are well-scoped for new contributors.

Areas where contributions are especially welcome:

- **Documentation** — SDK examples, integration guides, verifier usage patterns
- **Test coverage** — additional verifier cases, especially malformed and adversarial inputs
- **SDK improvements** — TypeScript SDK parity with Python SDK
- **CLI enhancements** — additional forensic verification output formats

## Questions?

Open an issue. Help with your own system is an advisory engagement; see
[SUPPORT.md](SUPPORT.md).

## License

By contributing, you agree that your contributions will be licensed under the license
of the directory they land in: MIT for `cli/` and `sdk/`, Apache-2.0 for the CPEX plugin.
See [LICENSE](LICENSE).
