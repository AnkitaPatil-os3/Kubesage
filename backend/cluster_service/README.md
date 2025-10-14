# KubeSage Cluster Service

The Cluster Service is a microservice that provides on-demand Kubernetes cluster operations. It authenticates requests via API keys through RabbitMQ communication with the User Service and communicates with Kubernetes agents via WebSockets to retrieve cluster information.

## Features

- **API Key Authentication**: Secure authentication via RabbitMQ communication with User Service
- **On-Demand Namespace Listing**: Retrieve namespaces from Kubernetes clusters via agent communication
- **WebSocket Communication**: Real-time communication with Kubernetes agents
- **Rate Limiting**: Built-in rate limiting for API endpoints
- **Health Monitoring**: Health check endpoints for service monitoring
- **SSL/TLS Support**: Configurable SSL/TLS for production deployments

## Architecture

```
┌─────────────────┐    RabbitMQ     ┌─────────────────┐
│ Cluster Service │ ◄──────────────► │  User Service   │
└─────────────────┘   (Auth Req)    └─────────────────┘
         │
         │ RabbitMQ
         ▼
┌─────────────────┐    WebSocket    ┌─────────────────┐
│Onboarding Service│ ◄──────────────► │ Kubernetes Agent│
└─────────────────┘   (Namespace)   └─────────────────┘
```

## API Endpoints

### Authentication
All endpoints require an `X-API-Key` header with a valid API key.

### GET /api/v3.0/cluster/health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "cluster_service",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "version": "1.0.0"
}
```

### GET /api/v3.0/cluster/namespaces
Get namespaces from a Kubernetes cluster.

**Parameters:**
- `agent_id` (required): The unique identifier of the Kubernetes agent
- `cluster_id` (optional): Cluster ID for additional context

**Headers:**
- `X-API-Key`: Valid API key for authentication

**Response:**
```json
{
  "success": true,
  "agent_id": "agent-uuid",
  "cluster_id": 123,
  "namespaces": [
    {
      "name": "default",
      "status": "Active",
      "created_at": "2024-01-01T12:00:00Z",
      "labels": {"kubernetes.io/managed-by": "system"},
      "annotations": {}
    }
  ],
  "total_count": 1,
  "message": "Successfully retrieved namespaces from cluster",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### GET /api/v3.0/cluster/agents/connected
Get list of currently connected agents.

**Response:**
```json
{
  "success": true,
  "connected_agents": ["agent-uuid-1", "agent-uuid-2"],
  "total_count": 2,
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Service host |
| `PORT` | `8008` | Service port |
| `DEBUG` | `true` | Debug mode |
| `USER_SERVICE_URL` | `https://10.0.32.106:8001` | User service URL for fallback auth |
| `RABBITMQ_HOST` | `localhost` | RabbitMQ host |
| `RABBITMQ_PORT` | `5672` | RabbitMQ port |
| `RABBITMQ_USER` | `guest` | RabbitMQ username |
| `RABBITMQ_PASSWORD` | `guest` | RabbitMQ password |
| `RABBITMQ_VHOST` | `/` | RabbitMQ virtual host |
| `WEBSOCKET_TIMEOUT` | `30` | WebSocket timeout in seconds |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `60` | Rate limit threshold |
| `USE_SSL` | `false` | Enable SSL/TLS |
| `SSL_KEYFILE` | `key.pem` | SSL key file |
| `SSL_CERTFILE` | `cert.pem` | SSL certificate file |

## Installation & Setup

### Prerequisites
- Python 3.11+
- RabbitMQ server running
- User Service running
- Onboarding Service running
- Kubernetes agents deployed

### Installation

1. **Clone and navigate to cluster service:**
   ```bash
   cd backend/cluster_service
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Generate SSL certificates (development):**
   ```bash
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
     -subj "/C=US/ST=Dev/L=Dev/O=KubeSage/CN=localhost"
   ```

6. **Start the service:**
   ```bash
   ./start-cluster-service.sh
   # Or manually:
   python -m app.main
   ```

### Docker Deployment

```bash
# Build the image
docker build -t kubesage-cluster-service .

# Run the container
docker run -d \
  --name cluster-service \
  -p 8008:8007 \
  -e RABBITMQ_HOST=rabbitmq \
  -e USER_SERVICE_URL=https://user-service:8001 \
  kubesage-cluster-service
```

## Message Queue Integration

### Authentication Flow
1. Cluster Service receives API request with API key
2. Sends authentication request to `cluster_auth_requests` queue
3. User Service validates API key and responds via `cluster_auth_results` queue
4. Cluster Service processes authenticated request

### Namespace Request Flow
1. Cluster Service sends namespace request to `cluster_namespace_requests` queue
2. Onboarding Service receives request and forwards to agent via WebSocket
3. Agent responds with namespace data via WebSocket
4. Onboarding Service forwards response to `cluster_namespace_results` queue
5. Cluster Service receives response and returns to client

### Queue Definitions

#### Outbound Queues (Cluster Service → Other Services)
- `cluster_auth_requests`: Authentication requests to User Service
- `cluster_namespace_requests`: Namespace requests to Onboarding Service

#### Inbound Queues (Other Services → Cluster Service)
- `cluster_auth_results`: Authentication responses from User Service
- `cluster_namespace_results`: Namespace responses from Onboarding Service

## Security Best Practices

### Production Deployment
- ✅ Use proper SSL/TLS certificates
- ✅ Enable rate limiting
- ✅ Secure RabbitMQ credentials
- ✅ Network isolation between services
- ✅ API key rotation policies
- ✅ Audit logging
- ✅ Input validation
- ✅ Error message sanitization

### Development
- ⚠️ Self-signed certificates acceptable
- ⚠️ Debug logging enabled
- ⚠️ Relaxed rate limits

## Monitoring & Logging

### Health Checks
- Service health: `GET /api/v3.0/cluster/health`
- RabbitMQ connectivity monitoring
- WebSocket connection status

### Logging
- Request/response logging
- Authentication events
- Error tracking
- Performance metrics

### Metrics
- Request rate and latency
- Authentication success/failure rates
- WebSocket connection status
- Queue message processing times

## Troubleshooting

### Common Issues

**1. Authentication Failures**
```
Error: Authentication failed
```
- Check API key validity
- Verify User Service connectivity
- Check RabbitMQ connectivity

**2. Agent Communication Failures**
```
Error: Failed to communicate with agent
```
- Verify agent is running and connected
- Check Onboarding Service connectivity
- Verify WebSocket connections

**3. Rate Limiting**
```
Error: Rate limit exceeded
```
- Reduce request frequency
- Check rate limit configuration
- Consider upgrading limits for high-volume users

### Debug Commands

```bash
# Check service health
curl -H "X-API-Key: your-api-key" http://localhost:8007/api/v3.0/cluster/health

# Test namespace endpoint
curl -H "X-API-Key: your-api-key" \
  "http://localhost:8007/api/v3.0/cluster/namespaces?agent_id=your-agent-id"

# Check logs
tail -f cluster_service.log

# Test RabbitMQ connectivity
rabbitmqctl list_queues | grep cluster
```

## Development

### Running Tests
```bash
# Unit tests
python -m pytest tests/

# Integration tests
python -m pytest tests/integration/

# Load tests
python -m pytest tests/load/
```

### Code Quality
```bash
# Linting
flake8 app/

# Type checking
mypy app/

# Security scanning
bandit -r app/
```

## Contributing

1. Follow existing code patterns
2. Add appropriate error handling
3. Include tests for new features
4. Update documentation
5. Follow security best practices

## License

Part of the KubeSage project. See main project LICENSE for details.
