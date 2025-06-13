#!/usr/bin/env python3
"""
Test script to verify the fixes for Kubernetes operations and chat functionality.
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.langchain_service import (
    check_kubernetes_availability,
    get_recent_events,
    check_pod_errors_all_namespaces,
    get_all_namespaces,
    list_pods_in_namespace,
    get_cluster_resources_summary,
    kubernetes_operation_tool,
    process_with_langchain
)
from app.logger import logger

async def test_kubernetes_functions():
    """Test individual Kubernetes functions."""
    print("🧪 Testing Kubernetes Functions")
    print("=" * 50)
    
    # Test 1: Check Kubernetes availability
    print("1. Testing Kubernetes availability...")
    k8s_available = check_kubernetes_availability()
    print(f"   Result: {'✅ Available' if k8s_available else '❌ Not available'}")
    
    if not k8s_available:
        print("   ⚠️ Kubernetes not available, skipping other tests")
        return False
    
    # Test 2: Get cluster summary
    print("\n2. Testing cluster summary...")
    try:
        summary = get_cluster_resources_summary()
        print(f"   Result: ✅ Success")
        print(f"   Summary: {summary[:200]}...")
    except Exception as e:
        print(f"   Result: ❌ Error: {e}")
    
    # Test 3: Get namespaces
    print("\n3. Testing get namespaces...")
    try:
        namespaces = get_all_namespaces()
        print(f"   Result: ✅ Success")
        print(f"   Namespaces: {namespaces[:200]}...")
    except Exception as e:
        print(f"   Result: ❌ Error: {e}")
    
    # Test 4: Get recent events (fixed version)
    print("\n4. Testing recent events...")
    try:
        events = get_recent_events(limit=5)
        print(f"   Result: ✅ Success")
        print(f"   Events: {events[:200]}...")
    except Exception as e:
        print(f"   Result: ❌ Error: {e}")
    
    # Test 5: Check pod errors
    print("\n5. Testing pod error check...")
    try:
        pod_errors = check_pod_errors_all_namespaces()
        print(f"   Result: ✅ Success")
        print(f"   Pod errors: {pod_errors[:200]}...")
    except Exception as e:
        print(f"   Result: ❌ Error: {e}")
    
    # Test 6: List pods
    print("\n6. Testing list pods...")
    try:
        pods = list_pods_in_namespace("all")
        print(f"   Result: ✅ Success")
        print(f"   Pods: {pods[:200]}...")
    except Exception as e:
        print(f"   Result: ❌ Error: {e}")
    
    return True

async def test_kubernetes_operation_tool():
    """Test the main Kubernetes operation tool with various inputs."""
    print("\n🔧 Testing Kubernetes Operation Tool")
    print("=" * 50)
    
    test_cases = [
        ("get all namespaces", "Natural language - namespaces"),
        ("list pods", "Natural language - pods"),
        ("check pod errors", "Natural language - pod errors"),
        ("show recent events", "Natural language - events"),
        ("cluster status", "Natural language - cluster status"),
        ('{"operation": "get_namespaces"}', "JSON - get namespaces"),
        ('{"operation": "get_pods", "namespace": "default"}', "JSON - get pods"),
        ('{"operation": "check_pod_errors"}', "JSON - check pod errors"),
        ('{"operation": "get_events", "limit": 5}', "JSON - get events"),
    ]
    
    for i, (input_str, description) in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {description}")
        print(f"   Input: {input_str}")
        try:
            result = kubernetes_operation_tool(input_str)
            print(f"   Result: ✅ Success")
            print(f"   Output: {result[:150]}...")
        except Exception as e:
            print(f"   Result: ❌ Error: {e}")

async def test_langchain_processing():
    """Test the LangChain processing with various chat messages."""
    print("\n🤖 Testing LangChain Processing")
    print("=" * 50)
    
    test_messages = [
        "get all namespaces",
        "list all pods",
        "check pod errors in all namespaces",
        "show me recent events",
        "what is the cluster status?",
        "create namespace test-kubesage",
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. Testing message: '{message}'")
        try:
            result = await process_with_langchain(
                user_message=message,
                memory=None,
                stream=False
            )
            
            if result["success"]:
                print(f"   Result: ✅ Success")
                response = result["response"]
                print(f"   Response: {response[:200]}...")
            else:
                print(f"   Result: ❌ Failed")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   Result: ❌ Exception: {e}")

async def main():
    """Main test function."""
    print("🚀 Starting Kubernetes and Chat Functionality Tests")
    print("=" * 60)
    
    try:
        # Test Kubernetes functions
        k8s_success = await test_kubernetes_functions()
        
        if k8s_success:
            # Test Kubernetes operation tool
            await test_kubernetes_operation_tool()
            
            # Test LangChain processing
            await test_langchain_processing()
        
        print("\n" + "=" * 60)
        print("🏁 Tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
