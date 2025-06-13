#!/usr/bin/env python3
"""
Test script for KubeSage Chat Service
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_TOKEN = "test-token"  # You might need to adjust this based on your auth setup

def test_health():
    """Test the health endpoint."""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
        else:
            print(f"❌ Health check failed")
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_kubernetes_debug():
    """Test Kubernetes debug endpoint."""
    print("Testing Kubernetes debug endpoint...")
    try:
        headers = {"Authorization": f"Bearer {TEST_USER_TOKEN}"}
        response = requests.get(f"{BASE_URL}/debug/kubernetes", headers=headers)
        print(f"Kubernetes Debug Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Kubernetes debug passed")
            print(f"Cluster info: {data.get('cluster_summary', '')[:200]}...")
        else:
            print(f"❌ Kubernetes debug failed")
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Kubernetes debug error: {e}")
        return False

def test_pod_errors_debug():
    """Test pod errors debug endpoint."""
    print("Testing pod errors debug endpoint...")
    try:
        headers = {"Authorization": f"Bearer {TEST_USER_TOKEN}"}
        response = requests.get(f"{BASE_URL}/debug/pod-errors", headers=headers)
        print(f"Pod Errors Debug Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pod errors debug passed")
            print(f"Pod errors: {data.get('pod_errors', '')[:200]}...")
        else:
            print(f"❌ Pod errors debug failed")
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Pod errors debug error: {e}")
        return False

def test_direct_chat(message):
    """Test direct chat debug endpoint."""
    print(f"Testing direct chat with message: '{message}'")
    try:
        headers = {"Authorization": f"Bearer {TEST_USER_TOKEN}"}
        response = requests.post(
            f"{BASE_URL}/debug/direct-chat",
            params={"message": message},
            headers=headers
        )
        print(f"Direct Chat Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            result = data.get('result', {})
            if result.get('success'):
                print(f"✅ Direct chat successful")
                print(f"Response: {result.get('response', '')[:300]}...")
            else:
                print(f"⚠️ Direct chat completed but with issues")
                print(f"Error: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ Direct chat failed")
            print(f"Error: {response.text}")
        print("-" * 50)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Direct chat error: {e}")
        print("-" * 50)
        return False

def test_chat_endpoint(message, stream=False):
    """Test the main chat endpoint."""
    print(f"Testing chat endpoint with message: '{message}' (stream={stream})")
    try:
        headers = {"Authorization": f"Bearer {TEST_USER_TOKEN}"}
        payload = {
            "message": message,
            "stream": stream
        }
        
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            headers=headers,
            stream=stream
        )
        
        print(f"Chat Status: {response.status_code}")
        
        if response.status_code == 200:
            if stream:
                print("✅ Streaming chat successful")
                print("Stream content:")
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])
                                if data.get('token'):
                                    print(data['token'], end='', flush=True)
                                elif data.get('done'):
                                    print(f"\n✅ Stream completed. Session: {data.get('session_id')}")
                                    break
                            except json.JSONDecodeError:
                                continue
            else:
                data = response.json()
                print(f"✅ Chat successful")
                print(f"Response: {data.get('content', '')[:300]}...")
                print(f"Session ID: {data.get('session_id')}")
        else:
            print(f"❌ Chat failed")
            print(f"Error: {response.text}")
        
        print("-" * 50)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        print("-" * 50)
        return False

def main():
    """Run all tests."""
    print("=== KubeSage Chat Service Test ===")
    
    # Test 1: Health check
    health_ok = test_health()
    print()
    
    if not health_ok:
        print("❌ Health check failed. Stopping tests.")
        return
    
    # Test 2: Kubernetes debug
    k8s_ok = test_kubernetes_debug()
    print()
    
    # Test 3: Pod errors debug
    pod_errors_ok = test_pod_errors_debug()
    print()
    
    if not k8s_ok:
        print("⚠️ Kubernetes not available. Skipping chat tests.")
        return
    
    # Test 4: Direct chat tests
    test_messages = [
        "check all errors related to pods in my all namespaces",
        "get all namespaces",
        "list all pods",
        "what is the cluster status?",
        "show me recent events"
    ]
    
    print("=== Testing Direct Chat Debug Endpoint ===")
    for message in test_messages:
        test_direct_chat(message)
        time.sleep(1)  # Small delay between requests
    
    # Test 5: Main chat endpoint tests
    print("=== Testing Main Chat Endpoint ===")
    for message in test_messages[:3]:  # Test fewer messages for main endpoint
        test_chat_endpoint(message, stream=False)
        time.sleep(1)
    
    print("=== Test Complete ===")

if __name__ == "__main__":
    main()