#!/bin/bash

# Set your authentication token
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzQ3OTgwNTc4fQ.lEDkD7Z6NKXzFiP8bOkuo6wz8J9VBNL-0t0zASJT-1Q"

# URL to test
URL="https://10.0.32.122:8001/users/me"

# Check if server is reachable
echo "Checking if server is reachable..."
health_check=$(curl -k -s -o /dev/null -w "%{http_code}" https://10.0.32.122:8001/health)
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
  response=$(curl -k -s -w "\nStatus code: %{http_code}" -H "Authorization: Bearer $TOKEN" $URL)
  status_code=$(echo "$response" | tail -n1 | cut -d' ' -f3)
  response_body=$(echo "$response" | sed '$d')
  
  if [ "$status_code" -eq 429 ]; then
    echo "Rate limit exceeded response: $response_body"
  elif [ "$status_code" -eq 500 ]; then
    echo "Server error: $response_body"
  elif [ "$status_code" -eq 000 ]; then
    echo "Error: Could not connect to server"
  elif [ "$status_code" -eq 401 ]; then
    echo "Error: Unauthorized - token might be invalid"
  else
    echo "Status code: $status_code"
    echo "Response: $response_body"
  fi
}



# Make 15 requests (should hit rate limit after 10)
for i in {1..15}; do
  make_request $i
  sleep 0.5  # Small delay between requests
done
