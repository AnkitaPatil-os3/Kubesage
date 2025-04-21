FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    openssl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs

# Generate self-signed SSL certificates if they don't exist
RUN if [ ! -f cert.pem ] || [ ! -f key.pem ]; then \
    apt-get update && apt-get install -y openssl && \
    openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=localhost" && \
    rm -rf /var/lib/apt/lists/*; \
    fi

# Set environment variables for HTTPS
ENV SSL_KEYFILE=key.pem
ENV SSL_CERTFILE=cert.pem



# Expose port 8004
EXPOSE 8004

# Command to run the application with HTTPS
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004", "--ssl-keyfile", "key.pem", "--ssl-certfile", "cert.pem"]
