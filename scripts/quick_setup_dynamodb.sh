#!/bin/bash
# Quick Setup Script for DynamoDB
# This script automates the entire DynamoDB setup process

set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   🗄️  TradeSimulator - DynamoDB Quick Setup                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Start Local DynamoDB
echo "📦 Step 1: Starting Local DynamoDB..."
./scripts/setup_local_dynamodb.sh

# Wait a bit for DynamoDB to be fully ready
echo ""
echo "⏳ Waiting for DynamoDB to be fully ready..."
sleep 5

# Step 2: Create Tables
echo ""
echo "📊 Step 2: Creating DynamoDB Tables..."
python scripts/create_dynamodb_tables.py --local

# Step 3: Test Connection
echo ""
echo "🧪 Step 3: Testing Database Connection..."
python scripts/test_dynamodb_connection.py

# Step 4: Instructions
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   ✅ DynamoDB Setup Complete!                                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Next Steps:"
echo ""
echo "   1. Update your .env file with these settings:"
echo ""
echo "      AWS_ACCESS_KEY_ID=local"
echo "      AWS_SECRET_ACCESS_KEY=local"
echo "      AWS_REGION=us-east-1"
echo "      DYNAMODB_LOCAL_ENDPOINT=http://localhost:8000"
echo ""
echo "   2. Start your bot:"
echo ""
echo "      python app.py"
echo ""
echo "   3. Look for this in logs (NO MORE 'MOCK MODE'):"
echo ""
echo "      ✅ DynamoDB connection initialized successfully"
echo ""
echo "🎉 Your bot will now use real DynamoDB instead of mock mode!"
echo ""

