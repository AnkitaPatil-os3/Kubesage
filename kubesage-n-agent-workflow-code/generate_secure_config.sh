#!/bin/bash
# Secure configuration generator for KubeSage

set -e

echo "🔐 KubeSage Security Configuration Generator"
echo "============================================="

# Generate secure secret key
echo "📝 Generating secure SECRET_KEY..."
SECRET_KEY=$(openssl rand -base64 32)

# Generate secure API keys
echo "📝 Generating secure default API key..."
API_KEY="ks_$(openssl rand -base64 24 | tr -d '/' | tr '+' '_')"

# Generate database password
echo "📝 Generating secure database password..."
DB_PASSWORD=$(openssl rand -base64 16 | tr -d '/')

# Create .env file for user service
cat > backend/user_service/.env << EOF
# KubeSage User Service Configuration
# Generated on $(date)
# WARNING: Keep this file secure and never commit to version control

# Application settings
APP_NAME=KubeSage User Authentication Service
DEBUG=false

# Security - CHANGE IN PRODUCTION
SECRET_KEY=${SECRET_KEY}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database Configuration - PostgreSQL (Recommended for production)
POSTGRES_USER=kubesage_user
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=kubesage_users
DATABASE_URL=postgresql://kubesage_user:${DB_PASSWORD}@localhost:5432/kubesage_users

# For development only - use PostgreSQL in production
# DATABASE_URL=sqlite:///./kubesage_users.db

# RabbitMQ Configuration
RABBITMQ_USER=kubesage
RABBITMQ_PASSWORD=${DB_PASSWORD}
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_VHOST=/

# Email Configuration (Configure for production)
MAIL_USERNAME=your-email@domain.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=noreply@yourdomain.com
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com

# SSL Configuration (Use proper certificates in production)
SSL_KEYFILE=key.pem
SSL_CERTFILE=cert.pem

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# OpenAI Integration (Optional)
# OPENAI_API_KEY=your-openai-key
# OPENAI_BASE_URL=https://api.openai.com/v1/
# OPENAI_MODEL=gpt-3.5-turbo
# LLM_TIMEOUT=30
EOF

# Create .env file for onboarding service  
cat > backend/onboarding_service/.env << EOF
# KubeSage Onboarding Service Configuration
# Generated on $(date)
# WARNING: Keep this file secure and never commit to version control

# Service Configuration
HOST=0.0.0.0
PORT=8006
DEBUG=false

# User Service URL
USER_SERVICE_URL=https://localhost:8001

# Database Configuration
POSTGRES_USER=kubesage_onboard
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=kubesage_onboard
DATABASE_URL=postgresql://kubesage_onboard:${DB_PASSWORD}@localhost:5432/kubesage_onboard

# For development only - use PostgreSQL in production
# DATABASE_URL=sqlite:///./kubesage_onboard.db

# RabbitMQ Configuration
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=kubesage
RABBITMQ_PASSWORD=${DB_PASSWORD}

# SSL Configuration
SSL_KEYFILE=key.pem
SSL_CERTFILE=cert.pem
EOF

# Create .env file for agent
cat > backend/agent/.env.template << EOF
# KubeSage Agent Configuration Template
# Copy this to .env and customize for your cluster

# Agent Configuration (Get from dashboard)
AGENT_ID=REPLACE_WITH_GENERATED_AGENT_ID
API_KEY=${API_KEY}

# Cluster Configuration
CLUSTER_NAME=my-production-cluster

# Backend Configuration (Use your actual domain)
BACKEND_URL=https://your-kubesage-domain.com:8006/onboard
BACKEND_WS_URL=wss://your-kubesage-domain.com:8006/ws

# WebSocket Server Configuration
PORT=9000

# Logging
DEBUG=false
LOG_LEVEL=INFO
EOF

echo "✅ Configuration files generated successfully!"
echo ""
echo "📁 Generated files:"
echo "   - backend/user_service/.env"
echo "   - backend/onboarding_service/.env" 
echo "   - backend/agent/.env.template"
echo ""
echo "🔑 Generated credentials:"
echo "   Secret Key: ${SECRET_KEY}"
echo "   DB Password: ${DB_PASSWORD}"
echo "   Sample API Key: ${API_KEY}"
echo ""
echo "⚠️  IMPORTANT SECURITY NOTES:"
echo "   1. Change default passwords in production"
echo "   2. Use managed databases (RDS, Cloud SQL) in production"
echo "   3. Use proper SSL certificates (Let's Encrypt, ACM)"
echo "   4. Enable database encryption at rest"
echo "   5. Use secrets management (Vault, AWS Secrets Manager)"
echo "   6. Regularly rotate API keys and secrets"
echo ""
echo "🚀 Next steps:"
echo "   1. Review and customize the .env files"
echo "   2. Generate proper SSL certificates"
echo "   3. Set up managed database"
echo "   4. Configure monitoring and logging"
echo "   5. Set up backup and disaster recovery"
