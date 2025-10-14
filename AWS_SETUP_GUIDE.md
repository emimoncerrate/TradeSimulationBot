# 🚀 AWS Setup Guide for Jain Global Trading Bot

This guide will help you set up all required AWS services for your trading bot to move from development mode to production-ready infrastructure.

## 📋 Prerequisites

### 1. AWS Account Setup
- [ ] **AWS Account** with billing enabled
- [ ] **AWS CLI** installed and configured
- [ ] **Sufficient permissions** for creating resources

### 2. Install AWS CLI (if not already installed)

**macOS:**
```bash
brew install awscli
```

**Linux:**
```bash
sudo apt-get install awscli
# or
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### 3. Configure AWS CLI
```bash
aws configure
```

You'll need:
- **AWS Access Key ID**: From IAM user or root account
- **AWS Secret Access Key**: Corresponding secret
- **Default region**: `us-east-1` (recommended for Bedrock access)
- **Output format**: `json`

## 🛠️ Setup Process

### Step 1: Run the Setup Script
```bash
./scripts/setup-aws-services.sh
```

This script will:
- ✅ Create 6 DynamoDB tables
- ✅ Set up IAM roles and policies
- ✅ Create CloudWatch log groups
- ✅ Update your .env file with real credentials
- ✅ Test all services

### Step 2: Verify Setup
After the script completes, test your bot locally:
```bash
python app.py
```

You should see:
- No more "Skipping AWS validation" messages
- Successful database connections
- Real AWS service integration

### Step 3: Deploy to Lambda (Optional)
```bash
./scripts/deploy-lambda.sh
```

## 📊 AWS Resources Created

### DynamoDB Tables
| Table Name | Purpose | Keys |
|------------|---------|------|
| `jain-trading-bot-trades` | Trade records | user_id, trade_id |
| `jain-trading-bot-positions` | Current positions | user_id, symbol |
| `jain-trading-bot-users` | User profiles | user_id |
| `jain-trading-bot-channels` | Approved channels | channel_id |
| `jain-trading-bot-portfolios` | Portfolio data | user_id |
| `jain-trading-bot-audit` | Audit logs | audit_id |

### IAM Resources
- **Role**: `jain-trading-bot-lambda-role`
- **Policy**: `jain-trading-bot-lambda-policy`
- **Permissions**: DynamoDB, Bedrock, CloudWatch Logs

### CloudWatch
- **Log Group**: `/aws/lambda/jain-trading-bot-lambda`
- **Retention**: 30 days

## 💰 Cost Estimates

| Service | Monthly Usage | Estimated Cost |
|---------|---------------|----------------|
| DynamoDB | 1M read/write operations | ~$1.25 |
| Bedrock (Claude 3) | 100K tokens/day | ~$9.00 |
| Lambda | 100K requests | ~$0.20 |
| CloudWatch Logs | 1GB logs | ~$0.50 |
| **Total** | | **~$10.95/month** |

## 🔧 Configuration Changes

After setup, your `.env` file will be updated with:

```bash
# Real AWS credentials (instead of 'local')
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Table configuration
DYNAMODB_TABLE_PREFIX=jain-trading-bot

# Lambda configuration
AWS_LAMBDA_FUNCTION_NAME=jain-trading-bot-lambda
CLOUDWATCH_LOG_GROUP=/aws/lambda/jain-trading-bot-lambda
```

## 🚨 Security Notes

⚠️ **IMPORTANT**: After setup, your `.env` file contains real AWS credentials.

- **Never commit** `.env` to version control
- **Backup** your `.env` file securely
- **Rotate credentials** periodically
- **Use IAM roles** in production instead of access keys

## 🧪 Testing Your Setup

### 1. Test Database Connection
```bash
python -c "
from services.database import DatabaseService
import asyncio

async def test():
    db = DatabaseService()
    print('Database connection successful!')

asyncio.run(test())
"
```

### 2. Test Bedrock Access
```bash
python -c "
import boto3
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
models = bedrock.list_foundation_models()
print(f'Bedrock access successful! Found {len(models[\"modelSummaries\"])} models')
"
```

### 3. Test Your Bot
```bash
python app.py
```

Look for:
- ✅ No "mock mode" messages
- ✅ "DatabaseService initialized successfully"
- ✅ Real AWS service connections

## 🔄 Rollback (if needed)

If you want to go back to development mode:

1. **Restore backup**:
   ```bash
   cp .env.backup.* .env
   ```

2. **Or manually edit** `.env`:
   ```bash
   AWS_ACCESS_KEY_ID=local
   AWS_SECRET_ACCESS_KEY=local
   ```

## 📞 Support

If you encounter issues:

1. **Check AWS CLI**: `aws sts get-caller-identity`
2. **Verify permissions**: Ensure your AWS user has necessary permissions
3. **Check region**: Some services (like Bedrock) aren't available in all regions
4. **Review logs**: Check CloudWatch logs for detailed error messages

## 🎉 Next Steps

After successful setup:

1. **Test trading functionality** with real data persistence
2. **Monitor costs** in AWS Console
3. **Set up alerts** for unusual activity
4. **Deploy to Lambda** for production use
5. **Configure API Gateway** for Slack webhooks

Your trading bot is now running on production-grade AWS infrastructure! 🚀