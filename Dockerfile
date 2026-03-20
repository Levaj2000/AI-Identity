# AI Identity — Multi-service Dockerfile
# Usage: docker compose build (SERVICE arg set by docker-compose.yml)

FROM python:3.11-slim

ARG SERVICE
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for psycopg2-binary
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Install shared library first (changes less often → better layer cache)
COPY common/ common/
RUN pip install --no-cache-dir -e common/

# Install service-specific deps
COPY ${SERVICE}/requirements.txt ${SERVICE}/requirements.txt
RUN pip install --no-cache-dir -r ${SERVICE}/requirements.txt

# Copy Alembic config (API runs migrations on startup)
COPY alembic.ini alembic.ini
COPY alembic/ alembic/

# Copy service code + helper scripts
COPY ${SERVICE}/ ${SERVICE}/
COPY scripts/ scripts/

# Run as non-root user
USER appuser
