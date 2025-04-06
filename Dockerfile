# Use an official Python runtime as a parent image
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV REDIS_URL=${REDIS_URL}

# Expose the port the app runs on
EXPOSE $PORT

# Run the web server
CMD ["gunicorn", "app.app:app"]