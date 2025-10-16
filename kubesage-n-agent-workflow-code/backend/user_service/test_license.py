import requests
import time
from datetime import datetime

def test_license_expiration():
    base_url = "https://10.0.32.122:8001"
    
    print("\n🔍 Testing License Expiration\n")
    
    # Test endpoints
    endpoints = [
        "api/v1.0/users/me",  # Protected endpoint
        "/api/v1.0/license/status",  # License status endpoint
    ]
    
    # Test for 3 minutes (1 minute beyond expiration)
    start_time = datetime.now()
    max_duration = 180  # 3 minutes in seconds
    
    while (datetime.now() - start_time).seconds < max_duration:
        current_time = datetime.now()
        elapsed = (current_time - start_time).seconds
        
        print(f"\n⏱️  Time elapsed: {elapsed} seconds")
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}")
                status = response.status_code
                content = response.json()
                
                print(f"\n🌐 Testing endpoint: {endpoint}")
                print(f"📊 Status code: {status}")
                print(f"📝 Response: {content}")
                
            except Exception as e:
                print(f"❌ Error testing {endpoint}: {str(e)}")
        
        # Wait 30 seconds before next check
        print("\n⏳ Waiting 30 seconds...")
        time.sleep(30)

if __name__ == "__main__":
    test_license_expiration()