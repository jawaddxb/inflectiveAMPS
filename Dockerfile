# ──────────────────────────────────────────────────────────────────
# Inflectiv Vertical Intelligence Node
# Single-command deployment for any vertical niche
# Usage: docker run -e PROFILE=defi -e INFLECTIV_API_KEY=xxx inflectiv/node
# ──────────────────────────────────────────────────────────────────

# Stage 1: Build dependencies
FROM python:3.12-slim AS builder
WORKDIR /build
COPY skills/inflectiv/scripts/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    && pip install --no-cache-dir --prefix=/install \
       requests python-dotenv schedule colorama

# Stage 2: Runtime image
FROM python:3.12-slim
LABEL maintainer="Inflectiv VINN" \
      description="Vertical Intelligence Node — earn $INAI by maintaining structured datasets" \
      version="1.0.0"

# Copy installed packages
COPY --from=builder /install /usr/local

# Node user (non-root)
RUN useradd -m -u 1000 node
WORKDIR /app

# Copy node files
COPY nodes/           ./nodes/
COPY profiles/        ./profiles/
COPY skills/          ./skills/
COPY prompts/         ./prompts/
COPY connector/       ./connector/

# Create data directory for registry persistence
RUN mkdir -p /data && chown node:node /data /app
USER node

# Environment defaults (override at runtime)
ENV PROFILE=defi \
    INFLECTIV_API_KEY="" \
    LLM_API_KEY="" \
    LLM_PROVIDER="openai" \
    WALLET_ADDRESS="" \
    REFRESH_OVERRIDE="" \
    LOG_LEVEL="INFO" \
    DATA_DIR=/data

# Healthcheck — verifies node can reach registry
HEALTHCHECK --interval=5m --timeout=30s --retries=3 \
  CMD python -c "import json; json.load(open('/data/node_registry.json'))" || exit 1

EXPOSE 8765

# Entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
USER root
RUN chmod +x /entrypoint.sh
USER node
ENTRYPOINT ["/entrypoint.sh"]
