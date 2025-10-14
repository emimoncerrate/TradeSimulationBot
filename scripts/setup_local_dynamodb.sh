#!/bin/bash
# Setup Local DynamoDB for Development
# This script starts a local DynamoDB instance using Docker

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   🗄️  Starting Local DynamoDB for Development                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "   Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is running"

# Stop existing DynamoDB container if it exists
if docker ps -a --format 'table {{.Names}}' | grep -q "local-dynamodb"; then
    echo "🔄 Stopping existing DynamoDB container..."
    docker stop local-dynamodb > /dev/null 2>&1 || true
    docker rm local-dynamodb > /dev/null 2>&1 || true
fi

# Start DynamoDB Local container
echo "🚀 Starting DynamoDB Local container..."
docker run -d \
    --name local-dynamodb \
    -p 8000:8000 \
    amazon/dynamodb-local:latest \
    -jar DynamoDBLocal.jar \
    -sharedDb

# Wait for DynamoDB to be ready
echo "⏳ Waiting for DynamoDB to be ready..."
sleep 5

# Test connection
echo "🧪 Testing DynamoDB connection..."
if curl -s http://localhost:8000 > /dev/null; then
    echo "✅ DynamoDB Local is running on port 8000"
else
    echo "❌ DynamoDB Local failed to start"
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   ✅ DynamoDB Local Setup Complete!                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 DynamoDB Local is now running at: http://localhost:8000"
echo "🔧 Next step: Create tables with create_dynamodb_tables.py"
echo ""