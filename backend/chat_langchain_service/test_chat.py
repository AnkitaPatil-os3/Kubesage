#!/usr/bin/env python3
"""
Test script for the chat service
"""
import requests
import json
import sys

# Configuration
BASE_URL = "https://10.0.32.122:7004/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzMiIsImV4cCI6MTc0OTY0NzMyNX0.AFPNZ1sDGVMP_mieBTzF7Ptp9FEh7vKHsjojDACYNZc"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", headers=headers, verify=False)
        print(f"Health Status: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Health check failed: {e}")

def test_kubectl_debug():
    """Test kubectl debug endpoint"""
    print("\nTesting kubectl debug endpoint...")
    try:
        response = requests.post(
            f"{BASE_URL}/debug/kubectl",
            headers=headers,
            params={"command": "get namespaces"},
            verify=False
        )
        print(f"Kubectl Debug Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Command: {result['command']}")
            print(f"Result: {result['result'][:500]}...")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Kubectl debug failed: {e}")

def test_pod_errors():
    """Test pod errors endpoint"""
    print("\nTesting pod errors endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/debug/pod-errors", headers=headers, verify=False)
        print(f"Pod Errors Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Pod Errors: {result['pod_errors'][:500]}...")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Pod errors check failed: {e}")

def test_chat(message):
    """Test chat endpoint"""
    print(f"\nTesting chat with message: '{message}'")
    try:
        payload = {
            "message": message,
            "stream": False
        }
        
        response = requests.post(
            f"{BASE_URL}/chat",
            headers=headers,
            json=payload,
            verify=False,
            timeout=120
        )
        
        print(f"Chat Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result['content'][:1000]}...")
            print(f"Session ID: {result['session_id']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Chat test failed: {e}")

if __name__ == "__main__":
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    print("=== KubeSage Chat Service Test ===")
    
    # Run tests
    test_health()
    test_kubectl_debug()
    test_pod_errors()
    
    # Test various chat scenarios
    test_messages = [
        "check all error of related to pod in my all namespace",
        "get all namespaces",
        "create namespace test-kubesage",
        "list all pods",
        "what is the cluster status?",
        "show me recent events"
    ]
    
    for message in test_messages:
        test_chat(message)
        print("-" * 50)
    
    print("=== Test Complete ===")