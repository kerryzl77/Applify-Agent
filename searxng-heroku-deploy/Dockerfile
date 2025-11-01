FROM searxng/searxng:latest

# Copy custom settings
COPY settings.yml /etc/searxng/settings.yml

# Expose port (Heroku uses $PORT env var)
EXPOSE 8080

# Use environment variable for port if provided
CMD sed -i "s/port: 8080/port: ${PORT:-8080}/" /etc/searxng/settings.yml && \
    /usr/local/searxng/dockerfiles/docker-entrypoint.sh
