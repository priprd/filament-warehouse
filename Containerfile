# OCI Standard Containerfile for Minions Filaments Warehouse
# Compatible with Podman, Buildah, Docker, and OCI-compliant container runtimes
FROM python:3.11-slim AS builder

LABEL org.opencontainers.image.title="Minions Filaments Warehouse" \
      org.opencontainers.image.description="3D Printing Filament Inventory & NFC Spool Weight Manager" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.authors="Minions Warehouse Team"

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final OCI Runtime Stage
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Minions Filaments Warehouse" \
      org.opencontainers.image.description="3D Printing Filament Inventory & NFC Spool Weight Manager" \
      org.opencontainers.image.version="1.0.0"

WORKDIR /app

# Install runtime database libraries (psycopg2 / mysql support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . /app

# Security: Create non-root unprivileged container user
RUN useradd --uid 10001 -m minionuser && chown -R minionuser:minionuser /app
USER minionuser

EXPOSE 8000

ENV PORT=8000 \
    PYTHONUNBUFFERED=1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
