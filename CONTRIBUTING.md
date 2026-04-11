# Contributing to AI Identity

Thanks for your interest in contributing to AI Identity! This guide will help you get started.

## Getting Started

1. **Fork the repository** and clone your fork locally
2. **Set up your development environment** — see [README.md](README.md#quick-start) for instructions
3. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 22+
- PostgreSQL (or use Docker)

### Quick Setup with Docker

```bash
make setup   # generates .env with security keys
make up      # builds and starts api + gateway + postgres
```

### Manual Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r api/requirements.txt -r gateway/requirements.txt
pip install -e common/
pip install -r requirements-dev.txt
```

## Running Tests

All tests must pass before submitting a PR:

```bash
# Run all tests
pytest -v

# Run specific test suites
pytest api/tests/       # API tests
pytest gateway/tests/   # Gateway tests
pytest common/tests/    # Shared library tests
```

## Code Style

We use **Ruff** for both linting and formatting. CI will reject PRs that don't pass these checks.

```bash
# Check for lint errors
ruff check .

# Auto-fix lint errors
ruff check --fix .

# Check formatting
ruff format --check .

# Auto-format
ruff format .
```

For the dashboard (React/TypeScript):

```bash
cd dashboard
npm run lint          # ESLint
npm run format:check  # Prettier
npm run format        # Auto-format with Prettier
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
- [ ] Dashboard builds if frontend changes (`cd dashboard && npm run build`)
- [ ] New features include tests
- [ ] Database schema changes include an Alembic migration

## Project Structure

| Directory | What Lives Here |
|-----------|----------------|
| `api/` | FastAPI identity service (port 8001) |
| `gateway/` | FastAPI proxy gateway (port 8002) |
| `common/` | Shared models, schemas, auth, config |
| `dashboard/` | React + TypeScript frontend |
| `sdk/` | Python, TypeScript, and LangChain SDKs |
| `cli/` | Offline forensic verification CLI |
| `alembic/` | Database migrations |

## Where to Help

Check the [issues labeled `good first issue`](https://github.com/Levaj2000/AI-Identity/labels/good%20first%20issue) for tasks that are well-scoped for new contributors.

Areas where contributions are especially welcome:

- **Documentation** — SDK examples, integration guides, API usage patterns
- **Test coverage** — Additional test cases for gateway policies and edge cases
- **SDK improvements** — TypeScript SDK parity with Python SDK
- **CLI enhancements** — Additional forensic verification output formats

## Questions?

Open a [Discussion](https://github.com/Levaj2000/AI-Identity/discussions) or comment on an existing issue. We're happy to help you get oriented.

## License

By contributing, you agree that your contributions will be licensed under the project's existing license terms.
