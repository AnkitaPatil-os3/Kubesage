FROM python:3.11-slim
 
WORKDIR /app
 
# Install necessary system packages, kubectl, helm, and k8sgpt in one layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        gnupg2 \
        wget \
        dpkg \
        apt-transport-https \
        openssl \
        ca-certificates && \
    # Install kubectl
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/ && \
    # Install Helm
    curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | tee /usr/share/keyrings/helm.gpg > /dev/null && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | tee /etc/apt/sources.list.d/helm-stable-debian.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends helm && \
    # Download and install the k8sgpt .deb package
    wget https://github.com/k8sgpt-ai/k8sgpt/releases/download/v0.4.1/k8sgpt_amd64.deb && \
    dpkg -i k8sgpt_amd64.deb && \
    rm k8sgpt_amd64.deb && \
    # Clean up apt cache
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
 
# Copy requirements file first for better layer caching
COPY requirements.txt .
 
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
 
# Generate self-signed SSL certificate (openssl is already installed)
RUN openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/CN=k8sgpt-service"
 
# Copy application code
COPY . .
 
# Create necessary directories
RUN mkdir -p logs analysis_results
 
# Set environment variables for HTTPS
ENV SSL_KEYFILE=key.pem
ENV SSL_CERTFILE=cert.jjpem

# Expose port 8003 instead of 8002
EXPOSE 8003
 
# Command to run the application on port 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--ssl-keyfile", "key.pem", "--ssl-certfile", "cert.pem"]
