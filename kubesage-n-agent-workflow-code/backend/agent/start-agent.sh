#!/bin/bash

# KubeSage Agent Startup Script
echo "Starting KubeSage Agent..."

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | xargs)
    echo "Loaded environment variables from .env file"
else
    echo "Warning: .env file not found"
fi

# Validate required environment variables
if [ -z "$AGENT_ID" ]; then
    echo "Error: AGENT_ID environment variable is required"
    exit 1
fi

if [ -z "$API_KEY" ]; then
    echo "Error: API_KEY environment variable is required"
    exit 1
fi

if [ -z "$BACKEND_URL" ]; then
    echo "Error: BACKEND_URL environment variable is required"
    exit 1
fi

echo "Agent ID: $AGENT_ID"
echo "Backend URL: $BACKEND_URL"
echo "Port: ${PORT:-9000}"

# Build and run the agent
echo "Building agent..."
go mod tidy
go build -o kubesage-agent .

echo "Starting agent..."
./kubesage-agent
