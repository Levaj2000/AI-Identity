# Ada — Cloud Run image.
#
# Single-stage build. Python 3.13 to match the venv used in dev (the ADK
# stack runs cleanly on 3.13). Build context is the repository root so
# the image can pick up agent/ alongside any future shared modules.
#
# Build:
#   docker build -f agent/Dockerfile -t ada:dev .
# Run locally:
#   docker run -p 8000:8000 -e ADA_REQUIRE_AUTH=0 -e ADA_REQUIRE_AUDIT=0 ada:dev
# Cloud Run sets PORT; serve.py respects it.

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/agent

# System deps:
#   git → /version captures the startup SHA via `git rev-parse HEAD`
#   ripgrep → search_code prefers rg over grep when available
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ripgrep \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first so a code-only change keeps the layer cache.
COPY agent/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source. The .dockerignore alongside this file excludes the venv,
# build artifacts, dotfiles, and tests so the image stays small.
COPY agent/ ./

# Cloud Run runs containers as a non-root user by default; create one
# explicitly so file permissions are predictable.
RUN useradd --create-home --shell /bin/bash --uid 1000 ada \
    && chown -R ada:ada /app
USER ada

# Production defaults — flip auth + audit on. Override at deploy time
# only if there's a deliberate reason. The env-var contract is in
# docs/ada-deployment.md.
ENV ADA_REQUIRE_AUTH=1 \
    ADA_REQUIRE_AUDIT=1 \
    AI_IDENTITY_API_URL=https://api.ai-identity.co \
    AI_IDENTITY_GATEWAY_URL=https://gateway.ai-identity.co \
    GOOGLE_GENAI_USE_VERTEXAI=1

EXPOSE 8000

# Cloud Run injects PORT; default to 8000 for `docker run` locally. Use
# `exec` so SIGTERM reaches uvicorn cleanly during scale-down.
CMD ["sh", "-c", "exec python serve.py --host 0.0.0.0 --port ${PORT:-8000}"]
