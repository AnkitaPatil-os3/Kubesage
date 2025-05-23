#!/bin/bash

# Set your authentication token (replace with a valid token)
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzQ3OTgwNTc4fQ.lEDkD7Z6NKXzFiP8bOkuo6wz8J9VBNL-0t0zASJT-1Q"
# URL to test - update with your actual server address
URL="https://10.0.32.106:8002/kubeconfig/list"

# Check if server is reachable
echo "Checking if server is reachable..."
health_check=$(curl -k -s -o /dev/null -w "%{http_code}" https://10.0.32.106:8002/health)
if [ "$health_check" != "200" ]; then
  echo "Error: Server is not reachable. Health check returned: $health_check"
  echo "Please make sure the server is running and accessible."
  exit 1
fi

# Verify token is valid
echo "Verifying token..."
token_check=$(curl -k -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" $URL)
if [ "$token_check" == "401" ]; then
  echo "Error: Token is invalid or expired. Please update the token."
  exit 1
fi

echo "Server is reachable and token is valid. Starting rate limit test..."
echo "------------------------------------------------------------"

# Function to make a request and display the result
make_request() {
  echo "Request $1:"
  # Save both status code and response body
  response_body=$(mktemp)
  response=$(curl -k -s -o "$response_body" -w "%{http_code}" -H "Authorization: Bearer $TOKEN" $URL)
  echo "Status code: $response"
  
  if [ "$response" -eq 429 ]; then
    echo "Rate limit exceeded!"
    # Display the rate limit error message
    detail=$(cat "$response_body" | jq -r '.detail' 2>/dev/null || cat "$response_body" | grep -o '"detail":"[^"]*"' | sed 's/"detail":"\(.*\)"/\1/' || echo "Too many requests. Try again later.")
    limit=$(cat "$response_body" | jq -r '.limit' 2>/dev/null || cat "$response_body" | grep -o '"limit":"[^"]*"' | sed 's/"limit":"\(.*\)"/\1/' || echo "10 requests per minute")
    echo "Error: $detail"
    echo "Limit: $limit"
  elif [ "$response" -eq 000 ]; then
    echo "Error: Could not connect to server"
  elif [ "$response" -eq 401 ]; then
    echo "Error: Unauthorized - token might be invalid or session expired"
    # Extract and display the error message
    error_detail=$(cat "$response_body" | jq -r '.detail' 2>/dev/null || cat "$response_body" | grep -o '"detail":"[^"]*"' | sed 's/"detail":"\(.*\)"/\1/' || echo "No detailed error message")
    echo "Error message: $error_detail"
    
    # Provide helpful guidance
    echo "This could be due to:"
    echo "1. Your token has expired"
    echo "2. The token is invalid or malformed"
    echo "3. Your session has been invalidated due to security policies"
    echo "4. Too many requests with the same token (rate limiting side effect)"
    
    # Suggest solutions
    echo ""
    echo "Try the following:"
    echo "- Generate a new token by logging in again"
    echo "- Wait a few minutes before trying again"
    echo "- Check if your user account is still active"
  elif [ "$response" -eq 404 ]; then
    echo "Error: Endpoint not found"
  elif [ "$response" -eq 500 ]; then
    echo "Error: Server error"
    cat "$response_body" | jq -r '.detail' 2>/dev/null || cat "$response_body" | grep -o '"detail":"[^"]*"' | sed 's/"detail":"\(.*\)"/\1/' || echo "Internal server error"
  fi
  
  # Clean up temp file
  rm -f "$response_body"
}

# Make 15 requests (should hit rate limit after 10)
for i in {1..15}; do
  make_request $i
  sleep 0.5  # Small delay between requests
done

echo "------------------------------------------------------------"
echo "Rate limit test completed."

