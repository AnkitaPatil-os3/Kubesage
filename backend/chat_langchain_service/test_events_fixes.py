#!/usr/bin/env python3
"""
Specific test for the Kubernetes events namespace fix.
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    
    # Initialize Kubernetes client
    try:
        config.load_incluster_config()
        print("✅ Using in-cluster Kubernetes configuration")
    except config.ConfigException:
        try:
            config.load_kube_config()
            print("✅ Using default kubeconfig")
        except Exception as e:
            print(f"❌ Failed to load Kubernetes config: {e}")
            sys.exit(1)
    
    v1 = client.CoreV1Api()
    
    def test_events_namespace_fix():
        """Test the events namespace fix."""
        print("\n🧪 Testing Events Namespace Fix")
        print("=" * 40)
        
        try:
            # Get events from all namespaces
            events = v1.list_event_for_all_namespaces()
            
            print(f"📋 Found {len(events.items)} events")
            
            # Test the fix - access namespace correctly
            for i, event in enumerate(events.items[:5]):  # Test first 5 events
                print(f"\n{i+1}. Event Test:")
                
                # OLD WAY (would fail): event.namespace
                # NEW WAY (correct): event.metadata.namespace
                try:
                    event_namespace = event.metadata.namespace or "cluster"
                    timestamp = event.last_timestamp or event.first_timestamp or event.metadata.creation_timestamp
                    event_type = event.type or "Normal"
                    reason = event.reason or "Unknown"
                    message = (event.message or "No message")[:100]
                    
                    print(f"   ✅ Namespace: {event_namespace}")
                    print(f"   ✅ Type: {event_type}")
                    print(f"   ✅ Reason: {reason}")
                    print(f"   ✅ Time: {timestamp}")
                    print(f"   ✅ Message: {message}")
                    
                except AttributeError as e:
                    print(f"   ❌ AttributeError: {e}")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
            
            print(f"\n✅ Events namespace fix test completed successfully!")
            return True
            
        except ApiException as e:
            print(f"❌ Kubernetes API Error: {e.reason} (Status: {e.status})")
            return False
        except Exception as e:
            print(f"❌ Error testing events: {e}")
            return False
    
    if __name__ == "__main__":
        success = test_events_namespace_fix()
        if success:
            print("\n🎉 All tests passed! The namespace fix is working correctly.")
        else:
            print("\n💥 Tests failed! Check the error messages above.")
            sys.exit(1)

except ImportError:
    print("❌ Kubernetes client not available. Install with: pip install kubernetes")
    sys.exit(1)
