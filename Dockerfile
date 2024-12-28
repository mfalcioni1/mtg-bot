# Use Python 3.12+ slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY src/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ .
COPY .env .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Use tini as init system
RUN apt-get update && apt-get install -y tini
ENTRYPOINT ["/usr/bin/tini", "--"]

# Command to run the bot
CMD ["python", "bot.py"] 