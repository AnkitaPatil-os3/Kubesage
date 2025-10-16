"""
Test configuration and fixtures for onboarding service tests
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock, AsyncMock
import uuid
from datetime import datetime

from app.main import app
from app.database import get_db
from app.models import Base, ClusterConfig, Agent
from app.auth import authenticate_request


# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database dependency override"""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    """Mock user data for authentication"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True,
        "roles": "Developer"
    }


@pytest.fixture
def mock_auth_success(mock_user):
    """Mock successful authentication"""
    async def mock_authenticate_request(api_key: str):
        if api_key == "valid_api_key":
            return mock_user
        raise Exception("Invalid API key")
    
    return mock_authenticate_request


@pytest.fixture
def mock_auth_failure():
    """Mock authentication failure"""
    async def mock_authenticate_request(api_key: str):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    return mock_authenticate_request


@pytest.fixture
def sample_agent(db_session, mock_user):
    """Create a sample agent in the database"""
    agent = Agent(
        agent_id=str(uuid.uuid4()),
        user_id=mock_user["id"],
        status="pending"
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture
def sample_cluster(db_session, mock_user):
    """Create a sample cluster in the database"""
    cluster = ClusterConfig(
        cluster_name="test-cluster",
        server_url="in-cluster",
        token="in-cluster-token",
        context_name="test-context",
        provider_name="kubernetes",
        tags='["test", "development"]',
        use_secure_tls=True,
        user_id=mock_user["id"],
        cluster_metadata='{"agent_version": "1.0.0", "node_count": 3}'
    )
    db_session.add(cluster)
    db_session.commit()
    db_session.refresh(cluster)
    return cluster


@pytest.fixture
def valid_cluster_data():
    """Valid cluster configuration data for testing"""
    return {
        "cluster_name": "new-test-cluster",
        "context_name": "new-test-context",
        "provider_name": "kubernetes",
        "tags": ["test", "new"],
        "use_secure_tls": True,
        "metadata": {
            "agent_version": "1.0.0",
            "node_count": 2,
            "kubernetes_version": "v1.28.0",
            "namespace_count": 5
        }
    }


@pytest.fixture
def valid_headers(sample_agent):
    """Valid headers for API requests"""
    return {
        "X-API-Key": "valid_api_key",
        "agent_id": sample_agent.agent_id
    }


@pytest.fixture
def invalid_headers():
    """Invalid headers for API requests"""
    return {
        "X-API-Key": "invalid_api_key",
        "agent_id": "invalid_agent_id"
    }


@pytest.fixture
def mock_rabbitmq():
    """Mock RabbitMQ publishing functions"""
    mock_publish = Mock()
    mock_publish_api_key = Mock()
    
    import app.rabbitmq
    original_publish = app.rabbitmq.publish_message
    original_publish_api_key = app.rabbitmq.publish_api_key_validation_request
    
    app.rabbitmq.publish_message = mock_publish
    app.rabbitmq.publish_api_key_validation_request = mock_publish_api_key
    
    yield {
        "publish_message": mock_publish,
        "publish_api_key_validation_request": mock_publish_api_key
    }
    
    # Restore original functions
    app.rabbitmq.publish_message = original_publish
    app.rabbitmq.publish_api_key_validation_request = original_publish_api_key


@pytest.fixture(autouse=True)
def mock_rate_limiter():
    """Mock rate limiter to allow all requests during testing"""
    import app.rate_limiter
    
    original_is_allowed = app.rate_limiter.rate_limiter.is_allowed
    
    async def mock_is_allowed(*args, **kwargs):
        return True
    
    app.rate_limiter.rate_limiter.is_allowed = mock_is_allowed
    
    yield
    
    # Restore original rate limiter
    app.rate_limiter.rate_limiter.is_allowed = original_is_allowed
