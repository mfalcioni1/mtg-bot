# Use Python 3.12+ slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY src/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for credentials and copy them
COPY auth/ /app/auth/

# Copy source code
COPY src/ .
COPY .env .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/auth/credentials.json

# Use tini as init system
RUN apt-get update && apt-get install -y tini
ENTRYPOINT ["/usr/bin/tini", "--"]

# Command to run the bot
CMD ["python", "bot.py"] 