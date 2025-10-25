# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install system dependencies including curl for health checks and Playwright dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libreoffice \
    libmagic1 \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libwayland-client0 \
    libpango-1.0-0 \
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
RUN mkdir -p /app/output /app/uploads /tmp/flask_session && \
    chmod 755 /app/output /app/uploads /tmp/flask_session && \
    chown -R appuser:appuser /app/output /app/uploads /tmp/flask_session

# Switch to non-root user
USER appuser

# Install Playwright browsers as appuser (after switching user)
# This ensures browsers are installed in the correct user home directory
RUN python -m playwright install chromium

# Define environment variables
ENV FLASK_APP=app/app.py
ENV PYTHONPATH=/app
ENV FLASK_ENV=production
ENV PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:$PORT/health || exit 1

# Run the application with gunicorn (will be overridden by heroku.yml)
CMD ["gunicorn", "app.app:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "120"]