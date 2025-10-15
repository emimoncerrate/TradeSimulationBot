# 🚀 Complete Trading Bot Setup Log

**Date:** October 7, 2025  
**Status:** ✅ COMPLETE - Production Ready  
**Time to Complete:** ~30 minutes  

This log documents the complete setup process for the Slack Trading Bot with real DynamoDB database and Alpaca Paper Trading integration.

---

## 📋 Prerequisites

Before starting, ensure you have:
- [ ] **macOS/Linux/Windows** with terminal access
- [ ] **Python 3.8+** installed
- [ ] **Docker Desktop** installed and running
- [ ] **Git** installed
- [ ] **Slack workspace** with admin access
- [ ] **Internet connection** for API access

---

## 🎯 What You'll Get

After following this setup, you'll have:
- ✅ **Real-time market data** from Finnhub API
- ✅ **Persistent database** with DynamoDB (local)
- ✅ **Professional paper trading** with Alpaca
- ✅ **Complete Slack integration** with `/trade` command
- ✅ **Multi-user support** with role-based permissions
- ✅ **Audit trail** and compliance logging
- ✅ **Portfolio tracking** that survives restarts

---

## 🛠️ Step-by-Step Setup Process

### Step 1: Clone and Setup Project

```bash
# Clone the repository
git clone <your-repo-url>
cd TradeSimulationBot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install additional required packages
pip install alpaca-trade-api awscli
```

### Step 2: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your actual values
```

**Required .env Configuration:**

```bash
# Basic Settings
ENVIRONMENT=development
DEBUG_MODE=true
LOG_LEVEL=INFO

# Slack Configuration (Get from https://api.slack.com/apps)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_APP_TOKEN=xapp-your-app-token-here
APPROVED_CHANNELS=C09H1R7KKP1  # Your Slack channel ID

# Market Data (Get free key from https://finnhub.io/)
FINNHUB_API_KEY=your-finnhub-api-key-here

# Database Configuration (Local DynamoDB)
AWS_ACCESS_KEY_ID=local
AWS_SECRET_ACCESS_KEY=local
AWS_REGION=us-east-1
DYNAMODB_LOCAL_ENDPOINT=http://localhost:8000
DYNAMODB_TABLE_PREFIX=jain-trading-bot

# Alpaca Paper Trading (Get from https://alpaca.markets/)
ALPACA_PAPER_API_KEY=PK-your-paper-key-here
ALPACA_PAPER_SECRET_KEY=your-paper-secret-here
ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets
ALPACA_PAPER_ENABLED=true
```

### Step 3: Set Up Local DynamoDB

**3.1 Start Docker Desktop**
```bash
# Make sure Docker is running
docker --version
```

**3.2 Create DynamoDB Setup Script**
```bash
# Create the setup script
cat > scripts/setup_local_dynamodb.sh << 'EOF'
#!/bin/bash
set -e

echo "🗄️ Starting Local DynamoDB for Development"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "   Please start Docker Desktop and try again."
    exit 1
fi

# Stop existing container if it exists
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
if curl -s http://localhost:8000 > /dev/null; then
    echo "✅ DynamoDB Local is running on port 8000"
else
    echo "❌ DynamoDB Local failed to start"
    exit 1
fi

echo "✅ DynamoDB Local Setup Complete!"
EOF

# Make it executable
chmod +x scripts/setup_local_dynamodb.sh

# Run the setup
./scripts/setup_local_dynamodb.sh
```

**3.3 Create Database Tables**
```bash
# Create table creation script
python3 scripts/create_dynamodb_tables.py --local

# Verify tables were created
python3 scripts/create_dynamodb_tables.py --local --list
```

**Expected Output:**
```
✅ Tables created: 6
   - jain-trading-bot-trades
   - jain-trading-bot-positions
   - jain-trading-bot-users
   - jain-trading-bot-channels
   - jain-trading-bot-portfolios
   - jain-trading-bot-audit
```

### Step 4: Get API Keys

**4.1 Finnhub API Key (Free)**
1. Go to https://finnhub.io/
2. Sign up for free account
3. Get your API key
4. Add to `.env`: `FINNHUB_API_KEY=your-key-here`

**4.2 Alpaca Paper Trading Keys (Free)**
1. Go to https://alpaca.markets/
2. Sign up for free account
3. Navigate to "Paper Trading" section
4. Generate API keys (they start with "PK")
5. Add to `.env`:
   ```bash
   ALPACA_PAPER_API_KEY=PK-your-key-here
   ALPACA_PAPER_SECRET_KEY=your-secret-here
   ALPACA_PAPER_ENABLED=true
   ```

**4.3 Slack App Configuration**
1. Go to https://api.slack.com/apps
2. Create new app "From scratch"
3. Add Bot Token Scopes: `chat:write`, `commands`, `users:read`
4. Install app to workspace
5. Get tokens and add to `.env`

### Step 5: Test Configuration

**5.1 Test Database Connection**
```bash
# Create simple test
python3 -c "
import boto3
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url='http://localhost:8000',
    aws_access_key_id='local',
    aws_secret_access_key='local',
    region_name='us-east-1'
)
tables = list(dynamodb.tables.all())
print(f'✅ DynamoDB: {len(tables)} tables found')
"
```

**5.2 Test Alpaca Connection**
```bash
# Test Alpaca
python3 -c "
import asyncio
from services.alpaca_service import AlpacaService

async def test():
    alpaca = AlpacaService()
    await alpaca.initialize()
    if alpaca.is_available():
        account = await alpaca.get_account()
        print(f'✅ Alpaca: \${account[\"cash\"]:,.2f} available')
    else:
        print('❌ Alpaca: Not configured')

asyncio.run(test())
"
```

**5.3 Test Market Data**
```bash
# Test Finnhub
python3 -c "
import requests, os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('FINNHUB_API_KEY')
url = f'https://finnhub.io/api/v1/quote?symbol=AAPL&token={api_key}'
response = requests.get(url)
if response.status_code == 200:
    price = response.json().get('c', 0)
    print(f'✅ Market Data: AAPL \${price}')
else:
    print('❌ Market Data: API error')
"
```

### Step 6: Start the Bot

```bash
# Start the trading bot
python app.py
```

**Expected Startup Logs:**
```
✅ DynamoDB connection initialized successfully
✅ Alpaca Paper Trading ACTIVE - Real execution enabled
✅ Enhanced /trade command with live market data registered successfully
🎯 Enhanced features available: live market data, auto-refresh, interactive controls
```

### Step 7: Test in Slack

1. Go to your Slack workspace
2. Type: `/trade AAPL`
3. You should see a modal with live market data
4. Enter quantity and execute a trade
5. Check that data persists by restarting the bot

---

## 🔍 Verification Checklist

After setup, verify these work:

- [ ] **DynamoDB Running**: `docker ps | grep dynamodb`
- [ ] **Tables Created**: 6 tables exist
- [ ] **Bot Starts**: No "MOCK MODE" messages
- [ ] **Slack Command**: `/trade AAPL` opens modal
- [ ] **Live Data**: Real prices displayed
- [ ] **Trade Execution**: Orders go to Alpaca
- [ ] **Data Persistence**: Restart bot, data remains

---

## 🗄️ Database Management

**View Database Without Running App:**
```bash
# Install database viewer
pip install awscli

# View all data
python3 view_database.py

# View specific table
AWS_ACCESS_KEY_ID=local AWS_SECRET_ACCESS_KEY=local \
aws dynamodb scan --table-name jain-trading-bot-users \
--endpoint-url http://localhost:8000 --region us-east-1
```

**Manage DynamoDB Container:**
```bash
# Check status
docker ps | grep dynamodb

# Stop DynamoDB (keeps data)
docker stop local-dynamodb

# Start DynamoDB again
docker start local-dynamodb

# Remove DynamoDB (deletes all data!)
docker rm -f local-dynamodb
```

---

## 🐛 Troubleshooting

### Problem: "Docker not running"
**Solution:** Start Docker Desktop application

### Problem: "Port 8000 already in use"
**Solution:** 
```bash
# Find what's using port 8000
lsof -i :8000
# Kill the process or use different port
```

### Problem: "Bot still in MOCK MODE"
**Solution:** Check `.env` file:
```bash
# This should be "local", not "mock-access-key-id"
AWS_ACCESS_KEY_ID=local
```

### Problem: "Alpaca not available"
**Solution:** 
- Verify API keys are correct
- Ensure `ALPACA_PAPER_ENABLED=true`
- Check keys start with "PK"

### Problem: "No market data"
**Solution:**
- Verify Finnhub API key
- Check internet connection
- Test API key at https://finnhub.io/

### Problem: "Slack command not working"
**Solution:**
- Verify bot tokens in `.env`
- Check bot is installed in workspace
- Ensure channel is in `APPROVED_CHANNELS`

---

## 📊 What Each Component Does

### **DynamoDB (Database)**
- **Purpose**: Persistent data storage
- **Tables**: Users, trades, positions, portfolios, channels, audit
- **Benefits**: Data survives restarts, multi-user support, fast queries

### **Alpaca Paper Trading**
- **Purpose**: Professional trading simulation
- **Features**: Real market data, realistic execution, $500K virtual cash
- **Benefits**: Zero risk, professional experience, portfolio tracking

### **Finnhub API**
- **Purpose**: Real-time market data
- **Features**: Live prices, market status, company info
- **Benefits**: Accurate data, free tier available

### **Slack Integration**
- **Purpose**: User interface
- **Features**: `/trade` command, interactive modals, real-time updates
- **Benefits**: Easy to use, team collaboration, mobile access

---

## 🎉 Success Metrics

Your setup is successful when:

1. **✅ No "MOCK MODE" in logs** - Using real database
2. **✅ Alpaca account shows in logs** - Paper trading active
3. **✅ Live prices in Slack** - Market data working
4. **✅ Trades appear in Alpaca dashboard** - Real execution
5. **✅ Data persists after restart** - Database working
6. **✅ Multiple users can trade** - Multi-user support

---

## 🚀 Next Steps

After successful setup:

1. **Add team members** to Slack workspace
2. **Configure user roles** in the database
3. **Set up monitoring** (optional)
4. **Deploy to AWS** for production (optional)
5. **Add more trading features** as needed

---

## 📚 Additional Resources

- **Alpaca Docs**: https://alpaca.markets/docs/
- **Finnhub API**: https://finnhub.io/docs/api
- **Slack API**: https://api.slack.com/
- **DynamoDB Local**: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html

---

## 🔒 Security Notes

- **Paper Trading Only**: All trades are simulated with virtual money
- **Local Database**: Data stored locally, not in cloud
- **API Keys**: Keep your API keys secure and never commit to git
- **Slack Tokens**: Rotate tokens regularly for security

---

**Setup Complete! 🎉**

Your trading bot is now ready for professional use with:
- Real-time market data
- Persistent database storage  
- Professional paper trading
- Complete Slack integration
- Multi-user support
- Audit trail and compliance

**Total Cost: $0** (All services have free tiers)
**Risk Level: Zero** (Paper trading only)
**Production Ready: Yes** ✅