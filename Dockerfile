# Use Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    netcat-traditional \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and set permissions
RUN groupadd -r redditbot && useradd -r -g redditbot redditbot

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
RUN pip install gunicorn==23.0.0

# Copy project files
COPY src/ /app/src/
COPY comment_templates.json products.json personas.json .env* /app/

# Create necessary directories and set permissions
RUN mkdir -p /app/src/static /app/src/templates && \
    touch /app/app.log /app/src/app.log /app/src/bot.log && \
    chown -R redditbot:redditbot /app

# Switch to non-root user
USER redditbot

# Expose port
EXPOSE 8080

# Create entrypoint script
RUN echo '#!/bin/bash\n\
cd /app && \
exec gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 4 --timeout 120 src.main:app\n'\
> /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Run the application
CMD ["/app/entrypoint.sh"] 