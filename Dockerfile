# The AI Architect Panel — Dockerfile
# Multi-stage build for Azure Container Apps deployment
#
# Build:
#   docker build -t ai-architect-panel .
#
# Run locally:
#   docker run -p 8501:8501 --env-file .env ai-architect-panel
#
# Deploy to Azure Container Apps:
#   az containerapp create --name ai-architect-panel \
#     --image <registry>.azurecr.io/ai-architect-panel:latest \
#     --environment <env-name> \
#     --ingress external --target-port 8501 \
#     --secrets nvidia-api-key=<your-key> \
#     --env-vars NVIDIA_API_KEY=secretref:nvidia-api-key

FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies needed for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ─── Runtime stage ───

FROM python:3.12-slim

# Create non-root user for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code with correct ownership
COPY --chown=appuser:appgroup . .

# Ensure runtime directories are writable by non-root user
RUN mkdir -p .freebuff/compliance_db .freebuff/traces .freebuff/audit && \
    chown -R appuser:appgroup .freebuff && \
    chmod 755 /app

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Streamlit configuration
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true

# Default demo mode — override via .env or Azure secrets
ENV DEMO_MODE=true

# Switch to non-root user
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.connect(('localhost',8501)); s.close()"

ENTRYPOINT ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
