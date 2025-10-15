# 🐳 Docker Setup for Slack Trading Bot

## 🚀 Quick Start

### 1. **Get Your Own API Keys** (Required)

**Slack App:**
1. Go to https://api.slack.com/apps
2. Create new app → "From scratch"
3. Get your tokens:
   - Bot Token (`SLACK_BOT_TOKEN`)
   - Signing Secret (`SLACK_SIGNING_SECRET`) 
   - App Token (`SLACK_APP_TOKEN`)

**Finnhub API:**
1. Sign up at https://finnhub.io/
2. Get your free API key

### 2. **Setup Environment**

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

**Required variables:**
```env
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token
FINNHUB_API_KEY=your-finnhub-key
APPROVED_CHANNELS=your-channel-id
```

### 3. **Run with Docker**

```bash
# Build and start
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f trading-bot

# Stop
docker-compose down
```

## 🔧 Development Mode

```bash
# Run with live code reload
docker-compose up --build -d
docker-compose exec trading-bot bash

# Inside container
python app.py
```

## 🛡️ Security Features

- ✅ **No API keys in Docker image**
- ✅ **Environment variables only**
- ✅ **Non-root user**
- ✅ **Mock mode for safe testing**
- ✅ **Health checks**

## 📊 Services Included

- **trading-bot** - Main Slack bot
- **redis** - Caching (optional)
- **dynamodb-local** - Local database (optional)

## 🔍 Troubleshooting

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs trading-bot

# Restart service
docker-compose restart trading-bot

# Clean rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up
```

## 🚀 Production Deployment

For production, use:
- Real AWS credentials
- Production Slack workspace
- External Redis/DynamoDB
- Load balancer
- Monitoring

**Never commit `.env` files to git!**