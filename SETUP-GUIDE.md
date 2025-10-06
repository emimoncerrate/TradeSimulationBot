# 🚀 Setup Guide - Jain Global Slack Trading Bot

## ✅ Configuration Test Results

Your application is **working correctly**! The configuration test shows:

- ✅ **Dependencies**: All Python packages installed
- ✅ **Services**: All 5 services initialized successfully
- ✅ **Application**: Core logic working properly
- ⚠️ **API Keys**: Missing (expected for fresh setup)

## 🔑 Required API Keys

To run the trading bot, you need these API keys:

### 1. **Slack App Setup** (Required)
1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: "Jain Global Trading Bot"
4. Workspace: Select your workspace
5. Get these tokens:
   - **Bot Token** (`xoxb-...`) → `SLACK_BOT_TOKEN`
   - **Signing Secret** → `SLACK_SIGNING_SECRET`
   - **App Token** (`xapp-...`) → `SLACK_APP_TOKEN`

### 2. **Finnhub API** (Required)
1. Go to https://finnhub.io/
2. Sign up for free account
3. Get your API key → `FINNHUB_API_KEY`

## 🛠️ Quick Setup

### Step 1: Copy Environment Template
```bash
cp .env.example .env
```

### Step 2: Edit Environment File
```bash
nano .env
```

Add your actual API keys:
```env
SLACK_BOT_TOKEN=xoxb-your-actual-bot-token
SLACK_SIGNING_SECRET=your-actual-signing-secret
SLACK_APP_TOKEN=xapp-your-actual-app-token
FINNHUB_API_KEY=your-actual-finnhub-key
```

### Step 3: Test Configuration
```bash
python3 -c "from config.settings import validate_environment; print('✅ Valid' if validate_environment() else '❌ Invalid')"
```

### Step 4: Run the Application
```bash
# Development mode (Socket Mode)
python3 app.py

# Or HTTP server mode
python3 -c "from app import run_http_server; run_http_server()"
```

## 🐳 Docker Setup (Alternative)

If you prefer Docker:

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f trading-bot
```

## 🔍 Troubleshooting

### Common Issues:

1. **"Invalid token" error**
   - Check your Slack tokens are correct
   - Ensure bot has proper permissions

2. **"Missing environment variables"**
   - Make sure `.env` file exists
   - Check all required variables are set

3. **Redis connection refused**
   - This is optional - app works without Redis
   - To enable: `docker-compose up redis`

## 📊 Services Status

Your application includes these services:
- ✅ **DatabaseService**: Data persistence
- ✅ **MarketDataService**: Real-time market data
- ✅ **RiskAnalysisService**: Trade risk analysis
- ✅ **TradingAPIService**: Trade execution
- ✅ **AuthService**: User authentication

## 🎯 Next Steps

1. Get your API keys (Slack + Finnhub)
2. Create `.env` file with your keys
3. Run the application
4. Test with `/help` command in Slack

**The application is ready to go - just add your API keys!** 🚀
