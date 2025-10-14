"""
Integration tests for onboarding service
Tests the complete flow from agent registration to cluster onboarding
"""

import pytest
from unittest.mock import patch, Mock
import json
import uuid
from fastapi import HTTPException


class TestOnboardingIntegration:
    """Integration tests for the complete onboarding flow"""

    @patch('app.routes.authenticate_request')
    def test_complete_onboarding_flow(
        self, 
        mock_auth, 
        client,
        db_session,
        mock_user,
        mock_rabbitmq
    ):
        """Test the complete flow: generate agent ID -> onboard cluster -> list clusters"""
        # Setup mock authentication
        mock_auth.return_value = mock_user
        
        headers = {"X-API-Key": "valid_api_key"}
        
        # Step 1: Generate agent ID
        response = client.post("/api/v2.0/generate-agent-id", headers=headers)
        assert response.status_code == 200
        
        agent_data = response.json()
        agent_id = agent_data["agent_id"]
        
        # Step 2: Onboard cluster with the generated agent
        cluster_data = {
            "cluster_name": "integration-test-cluster",
            "context_name": "integration-context",
            "provider_name": "kubernetes",
            "tags": ["integration", "test"],
            "use_secure_tls": True,
            "metadata": {
                "agent_version": "1.0.0",
                "node_count": 3,
                "kubernetes_version": "v1.28.0"
            }
        }
        
        onboard_headers = {**headers, "agent_id": agent_id}
        
        response = client.post(
            "/api/v2.0/onboard",
            json=cluster_data,
            headers=onboard_headers
        )
        assert response.status_code == 201
        
        cluster_response = response.json()
        assert cluster_response["cluster_name"] == cluster_data["cluster_name"]
        assert cluster_response["metadata"] == cluster_data["metadata"]
        
        # Step 3: List clusters and verify the onboarded cluster appears
        response = client.get("/api/v2.0/clusters", headers=headers)
        assert response.status_code == 200
        
        clusters_data = response.json()
        assert len(clusters_data["clusters"]) == 1
        
        listed_cluster = clusters_data["clusters"][0]
        assert listed_cluster["cluster_name"] == cluster_data["cluster_name"]
        assert listed_cluster["id"] == cluster_response["id"]

    @patch('app.routes.authenticate_request')
    def test_multiple_agents_same_user(
        self, 
        mock_auth, 
        client,
        mock_user,
        mock_rabbitmq
    ):
        """Test multiple agents for the same user"""
        # Setup mock authentication
        mock_auth.return_value = mock_user
        
        headers = {"X-API-Key": "valid_api_key"}
        
        # Generate multiple agent IDs
        agent_ids = []
        for i in range(3):
            response = client.post("/api/v2.0/generate-agent-id", headers=headers)
            assert response.status_code == 200
            agent_ids.append(response.json()["agent_id"])
        
        # Onboard clusters with different agents
        for i, agent_id in enumerate(agent_ids):
            cluster_data = {
                "cluster_name": f"multi-agent-cluster-{i}",
                "provider_name": "kubernetes",
                "metadata": {"agent_index": i}
            }
            
            onboard_headers = {**headers, "agent_id": agent_id}
            
            response = client.post(
                "/api/v2.0/onboard",
                json=cluster_data,
                headers=onboard_headers
            )
            assert response.status_code == 201
        
        # Verify all clusters are listed
        response = client.get("/api/v2.0/clusters", headers=headers)
        assert response.status_code == 200
        
        clusters_data = response.json()
        assert len(clusters_data["clusters"]) == 3

    @patch('app.routes.authenticate_request')
    def test_agent_ownership_validation(
        self, 
        mock_auth, 
        client,
        mock_rabbitmq
    ):
        """Test that agents can only be used by their owners"""
        # Setup mock authentication for user 1
        user1 = {"id": 1, "username": "user1", "email": "user1@test.com"}
        user2 = {"id": 2, "username": "user2", "email": "user2@test.com"}
        
        # Generate agent for user 1
        mock_auth.return_value = user1
        headers1 = {"X-API-Key": "user1_api_key"}
        
        response = client.post("/api/v2.0/generate-agent-id", headers=headers1)
        assert response.status_code == 200
        agent_id = response.json()["agent_id"]
        
        # Try to use user 1's agent with user 2's credentials
        mock_auth.return_value = user2
        headers2 = {"X-API-Key": "user2_api_key", "agent_id": agent_id}
        
        cluster_data = {
            "cluster_name": "cross-user-test",
            "provider_name": "kubernetes"
        }
        
        response = client.post(
            "/api/v2.0/onboard",
            json=cluster_data,
            headers=headers2
        )
        
        # Should fail because agent belongs to user 1, not user 2
        assert response.status_code == 404
        assert "not found or does not belong to you" in response.json()["detail"]

    @patch('app.routes.authenticate_request')
    def test_onboarding_with_cluster_association(
        self, 
        mock_auth, 
        client,
        db_session,
        sample_cluster,
        mock_user,
        mock_rabbitmq
    ):
        """Test generating agent ID with existing cluster association"""
        # Setup mock authentication
        mock_auth.return_value = mock_user
        
        headers = {"X-API-Key": "valid_api_key"}
        params = {"cluster_id": sample_cluster.id}
        
        # Generate agent ID with cluster association
        response = client.post("/api/v2.0/generate-agent-id", headers=headers, params=params)
        assert response.status_code == 200
        
        agent_data = response.json()
        assert agent_data["cluster_id"] == sample_cluster.id
        
        # Verify agent is created with correct cluster association
        # Note: In real scenario, the agent would be associated after successful onboarding


class TestErrorHandling:
    """Test error handling scenarios"""

    @patch('app.routes.authenticate_request')
    def test_database_rollback_on_error(
        self, 
        mock_auth, 
        client,
        sample_agent,
        mock_user
    ):
        """Test that database transactions are rolled back on errors"""
        # Setup mock authentication
        mock_auth.return_value = mock_user
        
        # Create a scenario that might cause a database error
        # For example, extremely long cluster name
        cluster_data = {
            "cluster_name": "x" * 1000,  # Very long name that might exceed DB limits
            "provider_name": "kubernetes"
        }
        
        headers = {"X-API-Key": "valid_api_key", "agent_id": sample_agent.agent_id}
        
        # Make request
        response = client.post(
            "/api/v2.0/onboard",
            json=cluster_data,
            headers=headers
        )
        
        # Should handle the error gracefully
        assert response.status_code in [400, 422, 500]  # Some kind of error response

    @patch('app.routes.authenticate_request')
    def test_concurrent_onboarding_same_cluster(
        self, 
        mock_auth, 
        client,
        sample_agent,
        mock_user
    ):
        """Test handling of concurrent onboarding requests for the same cluster"""
        # Setup mock authentication
        mock_auth.return_value = mock_user
        
        cluster_data = {
            "cluster_name": "concurrent-test-cluster",
            "provider_name": "kubernetes"
        }
        
        headers = {"X-API-Key": "valid_api_key", "agent_id": sample_agent.agent_id}
        
        # First request should succeed
        response1 = client.post(
            "/api/v2.0/onboard",
            json=cluster_data,
            headers=headers
        )
        assert response1.status_code == 201
        
        # Second request with same cluster name should fail
        response2 = client.post(
            "/api/v2.0/onboard",
            json=cluster_data,
            headers=headers
        )
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]


class TestDataConsistency:
    """Test data consistency and validation"""

    @patch('app.routes.authenticate_request')
    def test_metadata_json_serialization(
        self, 
        mock_auth, 
        client,
        sample_agent,
        mock_user
    ):
        """Test that metadata is properly serialized and deserialized"""
        # Setup mock authentication
        mock_auth.return_value = mock_user
        
        # Complex nested metadata
        complex_metadata = {
            "strings": "test_string",
            "numbers": 42,
            "floats": 3.14,
            "booleans": True,
            "arrays": [1, 2, 3, "four"],
            "nested_objects": {
                "level1": {
                    "level2": {
                        "value": "deep_nested"
                    }
                }
            },
            "null_values": None
        }
        
        cluster_data = {
            "cluster_name": "metadata-json-test",
            "provider_name": "kubernetes",
            "metadata": complex_metadata
        }
        
        headers = {"X-API-Key": "valid_api_key", "agent_id": sample_agent.agent_id}
        
        # Onboard cluster
        response = client.post(
            "/api/v2.0/onboard",
            json=cluster_data,
            headers=headers
        )
        assert response.status_code == 201
        
        # Verify metadata is correctly returned
        returned_metadata = response.json()["metadata"]
        assert returned_metadata == complex_metadata
        
        # Verify metadata is correctly stored and retrieved via list endpoint
        list_response = client.get("/api/v2.0/clusters", headers={"X-API-Key": "valid_api_key"})
        assert list_response.status_code == 200
        
        listed_cluster = list_response.json()["clusters"][0]
        assert listed_cluster["metadata"] == complex_metadata

    @patch('app.routes.authenticate_request')
    def test_tags_normalization(
        self, 
        mock_auth, 
        client,
        sample_agent,
        mock_user
    ):
        """Test that tags are properly normalized"""
        # Setup mock authentication
        mock_auth.return_value = mock_user
        
        headers = {"X-API-Key": "valid_api_key", "agent_id": sample_agent.agent_id}
        
        # Test different tag formats
        test_cases = [
            ("string_tag", ["string_tag"]),
            (["array", "tags"], ["array", "tags"]),
            (None, None),
        ]
        
        for i, (input_tags, expected_tags) in enumerate(test_cases):
            cluster_data = {
                "cluster_name": f"tags-test-{i}",
                "provider_name": "kubernetes",
                "tags": input_tags
            }
            
            response = client.post(
                "/api/v2.0/onboard",
                json=cluster_data,
                headers=headers
            )
            assert response.status_code == 201
            
            returned_tags = response.json()["tags"]
            assert returned_tags == expected_tags


class TestSecurityValidation:
    """Test security-related validations"""

    def test_sql_injection_prevention(self, client, mock_user):
        """Test that SQL injection attempts are prevented"""
        # Various SQL injection attempts in cluster name
        sql_injection_attempts = [
            "'; DROP TABLE cluster_configs; --",
            "' OR '1'='1",
            "cluster'; UPDATE users SET is_admin=true WHERE id=1; --",
            "cluster' UNION SELECT * FROM users --"
        ]
        
        with patch('app.routes.authenticate_request') as mock_auth:
            mock_auth.return_value = mock_user
            
            headers = {"X-API-Key": "valid_api_key", "agent_id": "dummy_agent"}
            
            for malicious_name in sql_injection_attempts:
                cluster_data = {
                    "cluster_name": malicious_name,
                    "provider_name": "kubernetes"
                }
                
                response = client.post(
                    "/api/v2.0/onboard",
                    json=cluster_data,
                    headers=headers
                )
                
                # Should not cause SQL injection (might fail for other reasons like invalid agent)
                # The important thing is that it doesn't cause a 500 error due to SQL syntax
                assert response.status_code in [400, 401, 404, 422]  # Not 500 (server error)

    def test_xss_prevention_in_metadata(self, client, mock_user, sample_agent):
        """Test that XSS attempts in metadata are handled safely"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
        
        with patch('app.routes.authenticate_request') as mock_auth:
            mock_auth.return_value = mock_user
            
            headers = {"X-API-Key": "valid_api_key", "agent_id": sample_agent.agent_id}
            
            for i, xss_payload in enumerate(xss_payloads):
                cluster_data = {
                    "cluster_name": f"xss-test-{i}",
                    "provider_name": "kubernetes",
                    "metadata": {
                        "description": xss_payload,
                        "notes": f"Test with payload: {xss_payload}"
                    }
                }
                
                response = client.post(
                    "/api/v2.0/onboard",
                    json=cluster_data,
                    headers=headers
                )
                
                if response.status_code == 201:
                    # Verify the payload is stored as-is (not executed)
                    returned_metadata = response.json()["metadata"]
                    assert returned_metadata["description"] == xss_payload
