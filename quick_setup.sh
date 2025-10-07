#!/bin/bash
# Quick Setup Script for TradeSimulator

echo "╔════════════════════════════════════════════════════╗"
echo "║   🚀 TradeSimulator Quick Setup                   ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Creating from template..."
    cp .env.example .env
fi

echo "📝 Let's configure your environment variables"
echo ""
echo "Please have ready:"
echo "  1. Slack Bot Token (xoxb-...)"
echo "  2. Slack Signing Secret"
echo "  3. Slack App Token (xapp-...)"
echo "  4. Finnhub API Key"
echo "  5. Slack Channel ID"
echo ""

read -p "Enter your Slack Bot Token (xoxb-...): " SLACK_BOT_TOKEN
read -p "Enter your Slack Signing Secret: " SLACK_SIGNING_SECRET
read -p "Enter your Slack App Token (xapp-...): " SLACK_APP_TOKEN
read -p "Enter your Finnhub API Key: " FINNHUB_API_KEY
read -p "Enter your Slack Channel ID (C...): " APPROVED_CHANNELS

# Update .env file
sed -i.bak "s/SLACK_BOT_TOKEN=.*/SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN/" .env
sed -i.bak "s/SLACK_SIGNING_SECRET=.*/SLACK_SIGNING_SECRET=$SLACK_SIGNING_SECRET/" .env
sed -i.bak "s/SLACK_APP_TOKEN=.*/SLACK_APP_TOKEN=$SLACK_APP_TOKEN/" .env
sed -i.bak "s/FINNHUB_API_KEY=.*/FINNHUB_API_KEY=$FINNHUB_API_KEY/" .env
sed -i.bak "s/APPROVED_CHANNELS=.*/APPROVED_CHANNELS=$APPROVED_CHANNELS/" .env

# Set development defaults
sed -i.bak "s/ENVIRONMENT=.*/ENVIRONMENT=development/" .env
sed -i.bak "s/DEBUG_MODE=.*/DEBUG_MODE=true/" .env
sed -i.bak "s/LOG_LEVEL=.*/LOG_LEVEL=INFO/" .env
sed -i.bak "s/MOCK_EXECUTION_ENABLED=.*/MOCK_EXECUTION_ENABLED=true/" .env

echo ""
echo "✅ Configuration saved to .env"
echo ""
echo "🔧 Installing dependencies..."

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "⚠️  Virtual environment not found. Installing globally..."
    pip3 install -r requirements.txt
fi

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║   ✅ Setup Complete!                              ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""
echo "To run the bot:"
echo "  python app.py"
echo ""
echo "Or with Docker:"
echo "  docker-compose up --build"
echo ""
