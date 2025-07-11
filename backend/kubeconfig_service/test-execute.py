#!/usr/bin/env python3
"""
Multi-user kubectl API testing script
Tests the execute-kubectl-direct API endpoint with concurrent users
"""

import asyncio
import aiohttp
import time
import json
import sys
from datetime import datetime

# Configuration
API_BASE_URL = "https://10.0.32.106:8002"  # Change to your API URL
CLUSTER_ID = 2  # Change to your cluster ID
NUM_USERS = 50  # Number of concurrent users (start with 50, then increase)
REQUESTS_PER_USER = 3  # Number of requests each user will make

# Test commands - safe kubectl commands that won't harm your cluster
TEST_COMMANDS = [
    {"command": "kubectl get pods --all-namespaces -o wide --no-headers | head -10"},
    {"command": "kubectl get nodes -o wide --no-headers"},
    {"command": "kubectl get services --all-namespaces -o wide --no-headers | head -10"},
    {"command": "kubectl get namespaces --no-headers"},
    {"command": "kubectl version --client"},
]

# Mock authentication tokens (replace with real tokens if needed)
def get_auth_headers(user_id):
    return {
        "Authorization": f"Bearer mock-token-user-{user_id}",
        "Content-Type": "application/json"
    }

class TestResults:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_time = 0
        self.response_times = []
        self.errors = []
        self.start_time = None
        self.end_time = None

    def add_result(self, success, response_time, error=None):
        self.total_requests += 1
        self.response_times.append(response_time)
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error:
                self.errors.append(error)

    def get_stats(self):
        if not self.response_times:
            return {}
        
        avg_response_time = sum(self.response_times) / len(self.response_times)
        min_response_time = min(self.response_times)
        max_response_time = max(self.response_times)
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            "avg_response_time": round(avg_response_time, 3),
            "min_response_time": round(min_response_time, 3),
            "max_response_time": round(max_response_time, 3),
            "total_test_time": round(self.end_time - self.start_time, 3) if self.start_time and self.end_time else 0,
            "requests_per_second": round(self.total_requests / (self.end_time - self.start_time), 2) if self.start_time and self.end_time else 0
        }

# Global results object
results = TestResults()

async def execute_kubectl_command(session, user_id, command_data):
    """Execute a single kubectl command for a user"""
    url = f"{API_BASE_URL}/kubeconfig/execute-kubectl-direct/{CLUSTER_ID}"
    headers = get_auth_headers(user_id)
    
    start_time = time.time()
    try:
        timeout = aiohttp.ClientTimeout(total=60)  # 60 second timeout
        async with session.post(url, json=command_data, headers=headers, timeout=timeout) as response:
            response_data = await response.json()
            end_time = time.time()
            response_time = end_time - start_time
            
            # Check if the request was successful
            success = response.status == 200 and response_data.get('success', False)
            
            if success:
                print(f"✅ User {user_id:3d} | {response_time:.3f}s | {command_data['command'][:50]}...")
            else:
                error_msg = response_data.get('error', 'Unknown error')
                print(f"❌ User {user_id:3d} | {response_time:.3f}s | Error: {error_msg[:50]}...")
                results.add_result(False, response_time, error_msg)
                return
            
            results.add_result(True, response_time)
            
    except asyncio.TimeoutError:
        end_time = time.time()
        response_time = end_time - start_time
        print(f"⏰ User {user_id:3d} | {response_time:.3f}s | TIMEOUT")
        results.add_result(False, response_time, "Timeout")
        
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        print(f"💥 User {user_id:3d} | {response_time:.3f}s | Exception: {str(e)[:50]}...")
        results.add_result(False, response_time, str(e))

async def simulate_user(session, user_id):
    """Simulate a single user making multiple requests"""
    print(f"🚀 Starting user {user_id}")
    
    for request_num in range(REQUESTS_PER_USER):
        # Select a command (rotate through available commands)
        command = TEST_COMMANDS[request_num % len(TEST_COMMANDS)]
        
        # Execute the command
        await execute_kubectl_command(session, user_id, command)
        
        # Small delay between requests from the same user
        await asyncio.sleep(0.1)
    
    print(f"✅ User {user_id} completed all requests")

async def run_load_test():
    """Run the main load test"""
    print(f"""
🧪 Kubectl API Load Test Starting
================================
API URL: {API_BASE_URL}
Cluster ID: {CLUSTER_ID}
Number of Users: {NUM_USERS}
Requests per User: {REQUESTS_PER_USER}
Total Requests: {NUM_USERS * REQUESTS_PER_USER}
Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
    
    results.start_time = time.time()
    
    # Create HTTP session with connection pooling
    connector = aiohttp.TCPConnector(
        limit=200,  # Total connection pool size
        limit_per_host=100,  # Max connections per host
        ttl_dns_cache=300,  # DNS cache TTL
        use_dns_cache=True,
    )
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Create tasks for all users
        tasks = []
        for user_id in range(1, NUM_USERS + 1):
            task = simulate_user(session, user_id)
            tasks.append(task)
        
        # Run all users concurrently
        print(f"🏃 Running {NUM_USERS} concurrent users...")
        await asyncio.gather(*tasks, return_exceptions=True)
    
    results.end_time = time.time()

def print_results():
    """Print test results"""
    stats = results.get_stats()
    
    print(f"""
📊 Test Results Summary
======================
Total Requests: {stats.get('total_requests', 0)}
Successful: {stats.get('successful_requests', 0)}
Failed: {stats.get('failed_requests', 0)}
Success Rate: {stats.get('success_rate', 0):.2f}%

⏱️  Performance Metrics
======================
Average Response Time: {stats.get('avg_response_time', 0):.3f}s
Min Response Time: {stats.get('min_response_time', 0):.3f}s
Max Response Time: {stats.get('max_response_time', 0):.3f}s
Total Test Duration: {stats.get('total_test_time', 0):.3f}s
Requests per Second: {stats.get('requests_per_second', 0):.2f}

End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
    
    # Print some error samples if any
    if results.errors:
        print("❌ Sample Errors:")
        for i, error in enumerate(results.errors[:5]):  # Show first 5 errors
            print(f"   {i+1}. {error}")
        if len(results.errors) > 5:
            print(f"   ... and {len(results.errors) - 5} more errors")

async def test_single_request():
    """Test a single request first to verify connectivity"""
    print("🔍 Testing single request first...")
    
    async with aiohttp.ClientSession() as session:
        await execute_kubectl_command(session, 999, TEST_COMMANDS[0])
    
    if results.successful_requests > 0:
        print("✅ Single request test passed!")
        return True
    else:
        print("❌ Single request test failed!")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1:
        global NUM_USERS
        try:
            NUM_USERS = int(sys.argv[1])
            print(f"Using {NUM_USERS} users from command line argument")
        except ValueError:
            print("Invalid number of users. Using default.")
    
    try:
        # Test single request first
        if not asyncio.run(test_single_request()):
            print("❌ Single request failed. Check your API URL and cluster ID.")
            return
        
        # Reset results for main test
        global results
        results = TestResults()
        
        # Run the main load test
        asyncio.run(run_load_test())
        
        # Print results
        print_results()
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"💥 Test failed with error: {str(e)}")

if __name__ == "__main__":
    main()

