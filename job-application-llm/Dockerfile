# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libreoffice \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip && \
    pip install httpx==0.24.1 && \
    pip install -r requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable for Flask
ENV FLASK_APP=app/app.py
ENV PYTHONPATH=/app

RUN echo "OPENAI_API_KEY=your_api_key_here" > .env

# Create necessary directories and set permissions
RUN mkdir -p /app/output /app/uploads && \
    chmod 777 /app/output /app/uploads

# Run the application
CMD ["python", "-m", "app.app"]