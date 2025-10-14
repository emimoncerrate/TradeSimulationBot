# Development Setup Guide

This guide will help you set up the Jain Global Trading Bot for local development.

## Quick Start (Automated)

Run the automated setup script:

```bash
./setup-dev.sh
```

This will automatically:
- ✅ Check Docker and Python
- ✅ Install dependencies
- ✅ Start DynamoDB Local and Redis
- ✅ Create all required database tables
- ✅ Verify configuration

## Manual Setup

If you prefer to set up manually or need to troubleshoot:

### 1. Prerequisites

- **Docker Desktop** - For running DynamoDB Local and Redis
- **Python 3.8+** - For running the application
- **Slack App** - With proper tokens configured in `.env`

### 2. Start Infrastructure Services

```bash
# Start DynamoDB Local and Redis
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 3. Create Database Tables

```bash
# Run the database setup script
python3 scripts/setup-local-db.py
```

This creates the following tables with proper indexes:
- `jain-trading-bot-users` (with GSI for Slack ID lookup)
- `jain-trading-bot-trades` (with user-timestamp index)
- `jain-trading-bot-positions` (with user index)
- `jain-trading-bot-channels`

### 4. Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

### 5. Configure Environment

Ensure your `.env` file has the correct values:

```env
# Development mode
ENVIRONMENT=development
DEBUG_MODE=true

# AWS (using local services)
AWS_ACCESS_KEY_ID=local
AWS_SECRET_ACCESS_KEY=local
DYNAMODB_LOCAL_ENDPOINT=http://localhost:8000

# Slack (replace with your actual tokens)
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token

# Market Data (replace with your actual API key)
FINNHUB_API_KEY=your-finnhub-api-key
```

### 6. Start the Application

```bash
python3 app.py
```

You should see:
```
⚡️ Bolt app is running!
```

## Verification

### Test Database Connection

```bash
# List tables in local DynamoDB
aws dynamodb list-tables --endpoint-url http://localhost:8000
```

### Test Slack Integration

1. Go to your Slack workspace
2. Type `/trade` in an approved channel
3. You should see the trading interface

## Troubleshooting

### DynamoDB Issues

```bash
# Check if DynamoDB Local is running
curl http://localhost:8000

# Restart DynamoDB Local
docker-compose restart dynamodb-local

# Reset all data
docker-compose down -v
./setup-dev.sh
```

### Slack Connection Issues

1. **Check tokens** - Ensure your Slack tokens are valid
2. **Check permissions** - Bot needs proper OAuth scopes
3. **Check channels** - Ensure channel ID is in `APPROVED_CHANNELS`

### Application Startup Issues

```bash
# Check configuration
python3 -c "from config.settings import ConfigurationManager; ConfigurationManager()"

# Check dependencies
pip3 install -r requirements.txt

# Check logs
python3 app.py 2>&1 | tee app.log
```

## Development Workflow

### Daily Development

```bash
# Start services
docker-compose up -d

# Start the bot
python3 app.py
```

### Reset Environment

```bash
# Stop everything and reset data
docker-compose down -v

# Re-run setup
./setup-dev.sh
```

### View Logs

```bash
# Application logs
python3 app.py

# Docker service logs
docker-compose logs -f dynamodb-local
docker-compose logs -f redis
```

## Production Deployment

For production deployment, you'll need:

1. **Real AWS credentials** with DynamoDB and Bedrock permissions
2. **Production Slack app** with proper OAuth configuration
3. **Environment variables** set to production values
4. **Monitoring and logging** configured

See the main README for production deployment instructions.

## Useful Commands

```bash
# View DynamoDB tables
aws dynamodb list-tables --endpoint-url http://localhost:8000

# Scan a table
aws dynamodb scan --table-name jain-trading-bot-users --endpoint-url http://localhost:8000

# Check Redis
docker exec -it redis-local redis-cli ping

# View Docker logs
docker-compose logs -f

# Stop services
docker-compose down

# Remove all data
docker-compose down -v
```