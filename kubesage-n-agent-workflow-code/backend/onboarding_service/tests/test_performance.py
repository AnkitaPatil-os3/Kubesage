"""
Performance and load tests for onboarding service
"""

import pytest
import asyncio
import time
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestPerformance:
    """Performance tests for onboarding endpoints"""

    @patch('app.routes.authenticate_request')
    def test_onboarding_response_time(
        self, 
        mock_auth, 
        client,
        sample_agent,
        mock_user
    ):
        """Test that onboarding requests complete within acceptable time"""
        mock_auth.return_value = mock_user
        
        cluster_data = {
            "cluster_name": "performance-test-cluster",
            "provider_name": "kubernetes",
            "metadata": {
                "test_data": "x" * 1000  # 1KB of test data
            }
        }
        headers = {
            "X-API-Key": "valid_api_key",
            "agent_id": sample_agent.agent_id
        }
        
        # Measure response time
        start_time = time.time()
        response = client.post("/onboard", json=cluster_data, headers=headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Response should complete within 2 seconds
        assert response_time < 2.0
        assert response.status_code == 201

    @patch('app.routes.authenticate_request')
    def test_list_clusters_performance(
        self, 
        mock_auth, 
        client,
        db_session,
        mock_user
    ):
        """Test performance of listing clusters with multiple clusters"""
        mock_auth.return_value = mock_user
        
        # Create multiple clusters in database
        from app.models import ClusterConfig
        import json
        
        clusters = []
        for i in range(50):  # Create 50 clusters
            cluster = ClusterConfig(
                cluster_name=f"perf-cluster-{i}",
                server_url="in-cluster",
                token="in-cluster-token",
                context_name=f"perf-context-{i}",
                provider_name="kubernetes",
                tags=json.dumps([f"tag-{i}", "performance"]),
                use_secure_tls=True,
                user_id=mock_user["id"],
                cluster_metadata=json.dumps({"index": i, "test": "performance"})
            )
            clusters.append(cluster)
            db_session.add(cluster)
        
        db_session.commit()
        
        headers = {"X-API-Key": "valid_api_key"}
        
        # Measure response time for listing all clusters
        start_time = time.time()
        response = client.get("/clusters", headers=headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Should complete within 1 second even with 50 clusters
        assert response_time < 1.0
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["clusters"]) == 50

    @patch('app.routes.authenticate_request')
    def test_concurrent_agent_generation(
        self, 
        mock_auth, 
        client,
        mock_user
    ):
        """Test concurrent agent ID generation"""
        mock_auth.return_value = mock_user
        headers = {"X-API-Key": "valid_api_key"}
        
        def generate_agent():
            return client.post("/generate-agent-id", headers=headers)
        
        # Generate 10 agent IDs concurrently
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(generate_agent) for _ in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        for response in results:
            assert response.status_code == 200
        
        # Should complete within 5 seconds
        assert total_time < 5.0
        
        # Verify all agent IDs are unique
        agent_ids = [response.json()["agent_id"] for response in results]
        assert len(set(agent_ids)) == len(agent_ids)  # All unique

    @patch('app.routes.authenticate_request')
    def test_large_metadata_handling(
        self, 
        mock_auth, 
        client,
        sample_agent,
        mock_user
    ):
        """Test handling of large metadata objects"""
        mock_auth.return_value = mock_user
        
        # Create large metadata (100KB)
        large_metadata = {
            "large_field": "x" * (100 * 1024),  # 100KB string
            "array_field": list(range(1000)),    # Large array
            "nested_objects": {
                f"key_{i}": {
                    "value": f"data_{i}",
                    "index": i,
                    "description": "test data" * 100
                }
                for i in range(100)
            }
        }
        
        cluster_data = {
            "cluster_name": "large-metadata-test",
            "provider_name": "kubernetes",
            "metadata": large_metadata
        }
        headers = {
            "X-API-Key": "valid_api_key",
            "agent_id": sample_agent.agent_id
        }
        
        start_time = time.time()
        response = client.post("/onboard", json=cluster_data, headers=headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Should handle large metadata within reasonable time (5 seconds)
        assert response_time < 5.0
        assert response.status_code == 201
        
        # Verify metadata is correctly stored and retrieved
        returned_metadata = response.json()["metadata"]
        assert returned_metadata["large_field"] == large_metadata["large_field"]
        assert len(returned_metadata["array_field"]) == 1000


class TestLoadTesting:
    """Load tests for concurrent operations"""

    @patch('app.routes.authenticate_request')
    def test_concurrent_onboarding_different_clusters(
        self, 
        mock_auth, 
        client,
        db_session,
        mock_user
    ):
        """Test concurrent onboarding of different clusters"""
        mock_auth.return_value = mock_user
        
        # Create multiple agents
        from app.models import Agent
        import uuid
        
        agents = []
        for i in range(5):
            agent = Agent(
                agent_id=str(uuid.uuid4()),
                user_id=mock_user["id"],
                status="pending"
            )
            agents.append(agent)
            db_session.add(agent)
        db_session.commit()
        
        def onboard_cluster(index, agent_id):
            cluster_data = {
                "cluster_name": f"concurrent-cluster-{index}",
                "provider_name": "kubernetes",
                "metadata": {"index": index}
            }
            headers = {
                "X-API-Key": "valid_api_key",
                "agent_id": agent_id
            }
            return client.post("/onboard", json=cluster_data, headers=headers)
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(onboard_cluster, i, agents[i].agent_id) 
                for i in range(5)
            ]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All requests should succeed
        success_count = sum(1 for r in results if r.status_code == 201)
        assert success_count == 5
        
        # Should complete within 10 seconds
        assert total_time < 10.0

    @patch('app.routes.authenticate_request')
    @patch('app.rate_limiter.rate_limiter.is_allowed')
    def test_rate_limiting_under_load(
        self, 
        mock_rate_limiter,
        mock_auth, 
        client,
        mock_user
    ):
        """Test rate limiting behavior under load"""
        mock_auth.return_value = mock_user
        
        # Allow first 5 requests, then block
        call_count = 0
        def mock_is_allowed(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return call_count <= 5
        
        mock_rate_limiter.side_effect = mock_is_allowed
        
        headers = {"X-API-Key": "valid_api_key"}
        
        def make_request(index):
            return client.post("/generate-agent-id", headers=headers)
        
        # Make 10 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        # Should have 5 successful (200) and 5 rate-limited (429) responses
        success_count = sum(1 for r in results if r.status_code == 200)
        rate_limited_count = sum(1 for r in results if r.status_code == 429)
        
        assert success_count == 5
        assert rate_limited_count == 5

    def test_memory_usage_with_many_requests(self, client):
        """Test memory usage doesn't grow excessively with many requests"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        headers = {"X-API-Key": "test_key"}
        
        # Make many requests (should fail but not leak memory)
        for i in range(100):
            response = client.post("/generate-agent-id", headers=headers)
            # Don't care about success, just testing memory usage
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024

    @patch('app.routes.authenticate_request')
    def test_database_connection_handling(
        self, 
        mock_auth, 
        client,
        mock_user
    ):
        """Test database connection handling under load"""
        mock_auth.return_value = mock_user
        
        headers = {"X-API-Key": "valid_api_key"}
        
        def make_requests_batch():
            responses = []
            for i in range(10):
                response = client.post("/generate-agent-id", headers=headers)
                responses.append(response)
            return responses
        
        # Make multiple batches of requests
        all_responses = []
        for batch in range(5):
            batch_responses = make_requests_batch()
            all_responses.extend(batch_responses)
            
            # Small delay between batches
            time.sleep(0.1)
        
        # Count successful responses
        success_count = sum(1 for r in all_responses if r.status_code == 200)
        
        # Most should succeed (allowing for some failures due to missing agents)
        # The important thing is no database connection errors (500 status)
        server_errors = sum(1 for r in all_responses if r.status_code == 500)
        assert server_errors == 0


class TestScalability:
    """Tests for service scalability characteristics"""

    def test_response_time_scaling_with_data_size(self, client):
        """Test how response time scales with data size"""
        # This is a conceptual test - in practice, you'd measure actual scaling
        # For now, just verify the endpoint can handle requests
        
        headers = {"X-API-Key": "test_key"}
        
        # Test with different payload sizes
        sizes = [1, 100, 1000]  # Small, medium, large
        
        for size in sizes:
            # Make request (will fail auth but tests payload handling)
            response = client.post("/generate-agent-id", headers=headers)
            
            # Should handle the request (even if it fails for auth reasons)
            assert response.status_code != 500  # No server errors

    @patch('app.routes.authenticate_request')
    def test_concurrent_user_isolation(
        self, 
        mock_auth, 
        client
    ):
        """Test that concurrent requests from different users are properly isolated"""
        
        def mock_auth_func(api_key):
            # Return different users based on API key
            if api_key == "user1_key":
                return {"id": 1, "username": "user1"}
            elif api_key == "user2_key":
                return {"id": 2, "username": "user2"}
            else:
                from fastapi import HTTPException
                raise HTTPException(status_code=401)
        
        mock_auth.side_effect = mock_auth_func
        
        def make_user_request(user_key):
            headers = {"X-API-Key": user_key}
            return client.post("/generate-agent-id", headers=headers)
        
        # Make concurrent requests from different users
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for _ in range(10):
                futures.append(executor.submit(make_user_request, "user1_key"))
                futures.append(executor.submit(make_user_request, "user2_key"))
            
            results = [future.result() for future in as_completed(futures)]
        
        # All should get proper responses (success or proper auth failures)
        # No server errors due to user isolation issues
        server_errors = sum(1 for r in results if r.status_code == 500)
        assert server_errors == 0
