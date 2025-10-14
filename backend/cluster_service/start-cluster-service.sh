#!/bin/bash

# Cluster Service Startup Script

echo "Starting KubeSage Cluster Service..."

# Set environment variables if not already set
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create SSL certificates if they don't exist (for development)
if [ ! -f "key.pem" ] || [ ! -f "cert.pem" ]; then
    echo "Generating self-signed SSL certificates for development..."
    openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
        -subj "/C=US/ST=Dev/L=Dev/O=KubeSage/CN=localhost"
    chmod 600 key.pem
fi

# Create logs directory
mkdir -p logs

# Start the service
echo "Starting Cluster Service on port 8008..."
python -m app.main
