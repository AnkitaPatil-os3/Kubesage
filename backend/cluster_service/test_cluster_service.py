#!/usr/bin/env python3
"""
Test script for Cluster Service functionality
"""
import asyncio
import httpx
import json
import sys
import os

# Configuration
CLUSTER_SERVICE_URL = "http://localhost:8007"
API_KEY = "ks_UeRAdTynu2XZmHzlOIsm6ypLSYrgkRXV"  # Example API key
AGENT_ID = "ccfebfe5-850e-4149-bcec-4c027fad9a4b"  # Example agent ID

async def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{CLUSTER_SERVICE_URL}/api/v3.0/cluster/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed: {data['status']}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {str(e)}")
            return False

async def test_namespaces_endpoint():
    """Test the namespaces endpoint"""
    print("🔍 Testing namespaces endpoint...")
    
    headers = {"X-API-Key": API_KEY}
    params = {"agent_id": AGENT_ID}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{CLUSTER_SERVICE_URL}/api/v3.0/cluster/namespaces",
                headers=headers,
                params=params,
                timeout=30.0
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Namespaces request successful")
                print(f"   Agent ID: {data.get('agent_id')}")
                print(f"   Total namespaces: {data.get('total_count', 0)}")
                if data.get('namespaces'):
                    print("   Namespaces:")
                    for ns in data['namespaces'][:5]:  # Show first 5
                        print(f"     - {ns.get('name')} ({ns.get('status')})")
                return True
            elif response.status_code == 401:
                print(f"❌ Authentication failed - check API key")
                return False
            elif response.status_code == 500:
                print(f"❌ Server error: {response.text}")
                return False
            else:
                print(f"❌ Unexpected response: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Namespaces request error: {str(e)}")
            return False

async def test_connected_agents():
    """Test the connected agents endpoint"""
    print("🔍 Testing connected agents endpoint...")
    
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{CLUSTER_SERVICE_URL}/api/v3.0/cluster/agents/connected",
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Connected agents request successful")
                print(f"   Total connected: {data.get('total_count', 0)}")
                if data.get('connected_agents'):
                    print("   Connected agents:")
                    for agent_id in data['connected_agents']:
                        print(f"     - {agent_id}")
                return True
            else:
                print(f"❌ Connected agents request failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Connected agents request error: {str(e)}")
            return False

async def test_invalid_api_key():
    """Test with invalid API key"""
    print("🔍 Testing invalid API key...")
    
    headers = {"X-API-Key": "invalid-key"}
    params = {"agent_id": AGENT_ID}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{CLUSTER_SERVICE_URL}/api/v3.0/cluster/namespaces",
                headers=headers,
                params=params,
                timeout=10.0
            )
            
            if response.status_code == 401:
                print(f"✅ Invalid API key correctly rejected")
                return True
            else:
                print(f"❌ Invalid API key should be rejected but got: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Invalid API key test error: {str(e)}")
            return False

async def test_missing_api_key():
    """Test with missing API key"""
    print("🔍 Testing missing API key...")
    
    params = {"agent_id": AGENT_ID}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{CLUSTER_SERVICE_URL}/api/v3.0/cluster/namespaces",
                params=params,
                timeout=10.0
            )
            
            if response.status_code == 422:  # FastAPI validation error
                print(f"✅ Missing API key correctly rejected")
                return True
            else:
                print(f"❌ Missing API key should be rejected but got: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Missing API key test error: {str(e)}")
            return False

async def main():
    """Run all tests"""
    print("🚀 Starting Cluster Service Tests")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health_check),
        ("Connected Agents", test_connected_agents),
        ("Missing API Key", test_missing_api_key),
        ("Invalid API Key", test_invalid_api_key),
        ("Namespaces Endpoint", test_namespaces_endpoint),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        result = await test_func()
        results.append((test_name, result))
        print()
    
    print("=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<8} {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 50)
    print(f"Total: {len(results)}, Passed: {passed}, Failed: {failed}")
    
    if failed > 0:
        print("\n⚠️  Some tests failed. Check the service configuration and try again.")
        sys.exit(1)
    else:
        print("\n🎉 All tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    # Check if service URL is reachable
    print(f"Testing Cluster Service at: {CLUSTER_SERVICE_URL}")
    print(f"Using API Key: {API_KEY[:20]}...")
    print(f"Using Agent ID: {AGENT_ID}")
    print()
    
    asyncio.run(main())
