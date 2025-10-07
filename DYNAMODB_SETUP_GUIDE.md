# 🗄️ DynamoDB Setup Guide for TradeSimulator

## 📋 Overview

This guide will help you switch from **Mock Mode** to **Real DynamoDB** for your TradeSimulator bot. You have two options:

1. **Local DynamoDB** (Recommended for development) - Free, runs on your machine
2. **AWS DynamoDB** (For production) - Cloud-based, scalable

---

## 🚀 Option 1: Local DynamoDB Setup (Recommended)

### Step 1: Start Local DynamoDB

```bash
# Make setup script executable
chmod +x scripts/setup_local_dynamodb.sh

# Run the setup script
./scripts/setup_local_dynamodb.sh
```

This will:
- ✅ Start DynamoDB Local in a Docker container
- ✅ Run on port 8000
- ✅ Create a persistent local database

### Step 2: Create Tables

```bash
# Activate virtual environment
source venv/bin/activate

# Create all DynamoDB tables
python scripts/create_dynamodb_tables.py --local

# Verify tables were created
python scripts/create_dynamodb_tables.py --local --list
```

You should see 6 tables created:
- ✅ slack-trading-bot-trades
- ✅ slack-trading-bot-positions
- ✅ slack-trading-bot-users
- ✅ slack-trading-bot-channels
- ✅ slack-trading-bot-portfolios
- ✅ slack-trading-bot-audit

### Step 3: Update Environment Variables

Edit your `.env` file and update these lines:

```bash
# FROM (Mock Mode):
# AWS_ACCESS_KEY_ID=mock-access-key-id
# AWS_SECRET_ACCESS_KEY=mock-secret-access-key

# TO (Local DynamoDB):
AWS_ACCESS_KEY_ID=local
AWS_SECRET_ACCESS_KEY=local
AWS_REGION=us-east-1
DYNAMODB_LOCAL_ENDPOINT=http://localhost:8000
DYNAMODB_TABLE_PREFIX=slack-trading-bot
```

**IMPORTANT**: The key change is `AWS_ACCESS_KEY_ID` - changing it from `mock-access-key-id` to `local` will switch from mock mode to real DynamoDB!

### Step 4: Test the Connection

```bash
# Run the test script
python scripts/test_dynamodb_connection.py
```

Expected output:
```
✅ DynamoDB connection successful!
✅ All 6 tables found
✅ Test user created
✅ Test trade logged
✅ Data retrieved successfully
```

### Step 5: Start Your Bot

```bash
# Start the bot
python app.py
```

Look for this in the logs:
```
✅ DynamoDB connection initialized successfully
✅ Table slack-trading-bot-users initialized successfully
✅ Table slack-trading-bot-trades initialized successfully
...
```

**No more "MOCK MODE" message!** 🎉

---

## ☁️ Option 2: AWS DynamoDB Setup (Production)

### Step 1: Install AWS CLI

```bash
# macOS
brew install awscli

# Or using pip
pip install awscli
```

### Step 2: Configure AWS Credentials

```bash
aws configure
```

Enter:
- AWS Access Key ID: `your-aws-access-key`
- AWS Secret Access Key: `your-aws-secret-key`
- Default region: `us-east-1`
- Default output format: `json`

### Step 3: Create Tables in AWS

```bash
# Create tables in AWS (not local)
python scripts/create_dynamodb_tables.py

# List tables to verify
python scripts/create_dynamodb_tables.py --list
```

### Step 4: Update Environment Variables

Edit your `.env` file:

```bash
# Use your real AWS credentials
AWS_ACCESS_KEY_ID=your-real-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-real-aws-secret-access-key
AWS_REGION=us-east-1

# Do NOT set DYNAMODB_LOCAL_ENDPOINT for AWS
# DYNAMODB_LOCAL_ENDPOINT=  # Comment out or remove

DYNAMODB_TABLE_PREFIX=slack-trading-bot
```

### Step 5: Test and Start

```bash
# Test connection
python scripts/test_dynamodb_connection.py

# Start bot
python app.py
```

---

## 🔍 Verification Checklist

After setup, verify these:

- [ ] DynamoDB container running (local) or AWS configured
- [ ] All 6 tables created
- [ ] Environment variables updated
- [ ] Bot starts without "MOCK MODE" message
- [ ] Test user can be created
- [ ] Trades can be logged
- [ ] `/trade` command works in Slack

---

## 🛠️ Useful Commands

### Local DynamoDB Management

```bash
# View container logs
docker logs local-dynamodb

# Stop DynamoDB
docker stop local-dynamodb

# Restart DynamoDB
docker restart local-dynamodb

# Remove DynamoDB (deletes all data!)
docker rm -f local-dynamodb

# List tables
aws dynamodb list-tables --endpoint-url http://localhost:8000

# Describe a table
aws dynamodb describe-table \
  --table-name slack-trading-bot-users \
  --endpoint-url http://localhost:8000
```

### View Data in Tables

```bash
# Scan users table (local)
aws dynamodb scan \
  --table-name slack-trading-bot-users \
  --endpoint-url http://localhost:8000

# Scan trades table (local)
aws dynamodb scan \
  --table-name slack-trading-bot-trades \
  --endpoint-url http://localhost:8000
```

---

## 🐛 Troubleshooting

### Problem: "Docker is not running"
**Solution**: Start Docker Desktop

### Problem: "Port 8000 already in use"
**Solution**: 
```bash
# Find what's using port 8000
lsof -i :8000

# Stop the process or use different port
docker run -d --name local-dynamodb -p 8001:8000 amazon/dynamodb-local
```

### Problem: "Table not found"
**Solution**: Run the create tables script again:
```bash
python scripts/create_dynamodb_tables.py --local
```

### Problem: "Bot still in MOCK MODE"
**Solution**: Check your `.env` file:
```bash
# This MUST NOT be "mock-access-key-id"
echo $AWS_ACCESS_KEY_ID

# Should be "local" or your real AWS key
```

### Problem: "NoCredentialsError"
**Solution**: 
- For local: Set `AWS_ACCESS_KEY_ID=local` and `AWS_SECRET_ACCESS_KEY=local`
- For AWS: Run `aws configure` to set up credentials

---

## 📊 What Data is Stored?

### Trades Table
- Every buy/sell trade execution
- Trade ID, symbol, quantity, price, timestamp
- User who made the trade
- Trade status (executed, pending, failed)

### Positions Table
- Current holdings for each user
- Symbol, quantity, average cost
- Real-time position tracking

### Users Table
- User profiles and authentication
- Slack user ID mapping
- Roles and permissions
- Portfolio manager assignments

### Channels Table
- Approved Slack channels
- Access control settings

### Portfolios Table
- Portfolio summaries
- Performance metrics
- Historical data

### Audit Table
- Complete audit trail
- All user actions
- Compliance logging

---

## 💰 Cost Estimate

### Local DynamoDB
- **Cost**: $0 (Free!)
- **Storage**: Limited by disk space
- **Performance**: Good for development

### AWS DynamoDB
- **Free Tier** (first 12 months):
  - 25 GB storage
  - 25 WCU + 25 RCU
  - Should cover development completely

- **Production** (after free tier):
  - ~$3-5/month for typical usage
  - Scales automatically
  - Pay per use

---

## 🎉 Benefits of Real DynamoDB

✅ **Persistent Data** - Survives bot restarts  
✅ **Multi-User Support** - True database isolation  
✅ **Fast Queries** - Indexed searches  
✅ **Scalable** - Handles thousands of users  
✅ **Audit Trail** - Complete compliance logging  
✅ **Backup & Recovery** - Automatic backups  
✅ **Production Ready** - Enterprise-grade database  

---

## 📚 Next Steps

After DynamoDB is working:

1. **Test trading flows** - Execute trades and verify they persist
2. **Check portfolios** - Restart bot and verify portfolio data remains
3. **Monitor performance** - Check CloudWatch metrics (AWS) or logs (local)
4. **Set up backups** - Configure automated backups (AWS)
5. **Optimize queries** - Add more indexes if needed

---

## 🆘 Need Help?

Check these files:
- `services/database.py` - Database service implementation
- `scripts/create_dynamodb_tables.py` - Table creation script
- `template.yaml` - AWS CloudFormation template
- `test_database_service.py` - Database tests

Your DynamoDB is ready to use! 🚀

