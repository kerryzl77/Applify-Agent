# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies (minimal set for production)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libreoffice \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt /app/requirements.txt

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app

# Verify client/dist exists and list its contents for debugging
RUN if [ -d "/app/client/dist" ]; then \
        echo "✓ client/dist directory found"; \
        echo "Contents:"; \
        ls -la /app/client/dist; \
    else \
        echo "✗ ERROR: client/dist directory NOT found!"; \
        echo "Creating empty dist directory as fallback"; \
        mkdir -p /app/client/dist; \
        echo '<html><body><h1>Frontend build missing</h1></body></html>' > /app/client/dist/index.html; \
    fi

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Create necessary directories and set permissions
RUN mkdir -p /app/output /app/uploads /tmp/app_session && \
    chmod 755 /app/output /app/uploads /tmp/app_session && \
    chown -R appuser:appuser /app/output /app/uploads /tmp/app_session

# Switch to non-root user
USER appuser

# Define environment variables
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:$PORT/health || exit 1

# Run the application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2", "--timeout-keep-alive", "180"]
