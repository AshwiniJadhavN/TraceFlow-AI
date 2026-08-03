# ============================================================================
# Stage 1: Builder
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /build

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 2: Runtime
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/traceflow/.local/bin:$PATH

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder --chown=1000:1000 /root/.local /home/traceflow/.local

# Copy application code
COPY --chown=1000:1000 agents/ ./agents/
COPY --chown=1000:1000 output/ ./output/
COPY --chown=1000:1000 prompts/ ./prompts/
COPY --chown=1000:1000 validators/ ./validators/
COPY --chown=1000:1000 main.py orchestrator.py system_orchestrator.py context.py ./

# Create non-root user
RUN useradd -m -u 1000 -d /home/traceflow traceflow || true

# Switch to non-root user
USER traceflow

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Entry point
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]

