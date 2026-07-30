# Dockerfile
# Use official Python slim image (smaller size, production-ready)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for cryptography)
# cryptography requires build tools on some platforms
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libssl-dev \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer caching optimization)
# If requirements.txt doesn't change, this layer is cached
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create non-root user for security (optional but recommended)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set Python to run in unbuffered mode (see logs immediately)
ENV PYTHONUNBUFFERED=1

# Health check (optional - ECS can use this)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#   CMD python -c "import boto3; print('healthy')" || exit 1

# Run the application
CMD ["python", "-m", "app.main"]