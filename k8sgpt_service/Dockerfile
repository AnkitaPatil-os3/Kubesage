FROM python:3.11-slim

WORKDIR /app

# Install necessary system packages including k8sgpt
RUN apt-get update && apt-get install -y curl gnupg2 && \
    curl -LO https://github.com/k8sgpt-ai/k8sgpt/releases/download/v0.3.18/k8sgpt_0.3.18_linux_amd64.tar.gz && \
    tar -xzf k8sgpt_0.3.18_linux_amd64.tar.gz && \
    mv k8sgpt /usr/local/bin/ && \
    chmod +x /usr/local/bin/k8sgpt && \
    rm k8sgpt_0.3.18_linux_amd64.tar.gz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Generate self-signed SSL certificate
RUN apt-get update && apt-get install -y openssl && \
    openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/CN=k8sgpt-service"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs analysis_results

# Expose port
EXPOSE 8002

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--ssl-keyfile", "key.pem", "--ssl-certfile", "cert.pem"]