#!/usr/bin/env python3
"""
Test script to verify Kubernetes Python client integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.langchain_service import (
    check_kubernetes_availability,
    check_pod_errors_all_namespaces,
    get_cluster_resources_summary,
    get_all_namespaces,
    get_recent_events,
    run_kubernetes_operation
)

def test_kubernetes_functions():
    """Test all Kubernetes functions."""
    print("=== Testing Kubernetes Python Client Integration ===\n")
    
    # Test 1: Check Kubernetes availability
    print("1. Testing Kubernetes availability...")
    k8s_available = check_kubernetes_availability()
    print(f"   Kubernetes available: {k8s_available}")
    
    if not k8s_available:
        print("   ❌ Kubernetes is not available. Please check your cluster configuration.")
        return False
    
    print("   ✅ Kubernetes is available\n")
    
    # Test 2: Get all namespaces
    print("2. Testing get all namespaces...")
    try:
        namespaces = get_all_namespaces()
        print(f"   Result: {namespaces[:200]}...")
        print("   ✅ Get namespaces successful\n")
    except Exception as e:
        print(f"   ❌ Get namespaces failed: {e}\n")
    
    # Test 3: Get cluster summary
    print("3. Testing cluster resources summary...")
    try:
        summary = get_cluster_resources_summary()
        print(f"   Result: {summary[:300]}...")
        print("   ✅ Cluster summary successful\n")
    except Exception as e:
        print(f"   ❌ Cluster summary failed: {e}\n")
    
    # Test 4: Check pod errors
    print("4. Testing pod errors check...")
    try:
        pod_errors = check_pod_errors_all_namespaces()
        print(f"   Result: {pod_errors[:300]}...")
        print("   ✅ Pod errors check successful\n")
    except Exception as e:
        print(f"   ❌ Pod errors check failed: {e}\n")
    
    # Test 5: Get recent events
    print("5. Testing recent events...")
    try:
        events = get_recent_events(limit=5)
        print(f"   Result: {events[:300]}...")
        print("   ✅ Recent events successful\n")
    except Exception as e:
        print(f"   ❌ Recent events failed: {e}\n")
    
    # Test 6: Kubernetes operations - get pods
    print("6. Testing Kubernetes operations (get pods)...")
    try:
        pods = run_kubernetes_operation("get_pods", namespace="all")
        print(f"   Result: {pods[:300]}...")
        print("   ✅ Get pods successful\n")
    except Exception as e:
        print(f"   ❌ Get pods failed: {e}\n")
    
    print("=== All tests completed ===")
    return True

if __name__ == "__main__":
    test_kubernetes_functions()