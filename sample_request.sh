#!/bin/bash

# Sample request for /self-heal endpoint
curl -X POST http://localhost:8000/self-heal \
    -H "Authorization: Bearer your_secure_token_here" \
    -H "Content-Type: application/json" \
    -d '{
        "event_data": {
            "metadata": {
                "name": "sample_incident",
                "namespace": "default"
            },
            "status": "open",
            "severity": "critical",
            "description": "Sample incident for testing"
        }
    }'