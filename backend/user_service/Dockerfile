FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
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

# Expose port 8001 instead of 8000
EXPOSE 8001

# Run the application with HTTPS on port 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--ssl-keyfile", "key.pem", "--ssl-certfile", "cert.pem"]
