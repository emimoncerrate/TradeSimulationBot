# Jain Global Slack Trading Bot - Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Jain Global Slack Trading Bot to AWS infrastructure. The deployment includes Lambda functions, API Gateway, DynamoDB tables, monitoring, and security configurations.

## Prerequisites

### Required Tools

1. **AWS CLI** (v2.0 or later)
   ```bash
   # Install AWS CLI
   curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
   sudo installer -pkg AWSCLIV2.pkg -target /
   
   # Configure AWS CLI
   aws configure
   ```

2. **SAM CLI** (v1.50 or later)
   ```bash
   # Install SAM CLI
   brew install aws-sam-cli
   
   # Verify installation
   sam --version
   ```

3. **Docker** (for local testing)
   ```bash
   # Install Docker Desktop
   # Download from: https://www.docker.com/products/docker-desktop
   ```

### AWS Account Setup

1. **IAM Permissions**: Ensure your AWS user/role has the following permissions:
   - CloudFormation full access
   - Lambda full access
   - API Gateway full access
   - DynamoDB full access
   - IAM role creation and management
   - CloudWatch full access
   - KMS key management (for production)

2. **AWS Region**: Choose an appropriate region (e.g., `us-east-1`, `us-west-2`)

3. **Account Limits**: Verify AWS service limits for your account

## Environment Configuration

### 1. Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here

# Market Data
FINNHUB_API_KEY=your-finnhub-api-key

# Optional Configuration
APPROVED_CHANNELS=C1234567890,C0987654321  # Comma-separated channel IDs
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
LOG_LEVEL=INFO
```

### 2. Slack App Configuration

Before deployment, you need to create and configure a Slack app:

1. **Create Slack App**:
   - Go to https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - Name: "Jain Trading Bot"
   - Workspace: Select your workspace

2. **OAuth & Permissions**:
   - Add the following Bot Token Scopes:
     - `app_mentions:read`
     - `channels:history`
     - `channels:read`
     - `chat:write`
     - `commands`
     - `groups:history`
     - `groups:read`
     - `im:history`
     - `im:read`
     - `im:write`
     - `mpim:history`
     - `mpim:read`
     - `mpim:write`
     - `users:read`

3. **App Home**:
   - Enable "Home Tab"
   - Enable "Messages Tab"

4. **Interactivity & Shortcuts**:
   - Enable Interactivity
   - Request URL: `https://your-api-gateway-url/slack/interactive` (will be set after deployment)

5. **Slash Commands**:
   - Create `/trade` command
   - Request URL: `https://your-api-gateway-url/slack/commands` (will be set after deployment)

6. **Event Subscriptions**:
   - Enable Events
   - Request URL: `https://your-api-gateway-url/slack/events` (will be set after deployment)
   - Subscribe to Bot Events:
     - `app_home_opened`
     - `app_mention`

## Deployment Process

### Step 1: Prepare for Deployment

1. **Clone and Navigate**:
   ```bash
   cd jain-global-slack-trading-bot
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Validate Configuration**:
   ```bash
   # Check environment variables
   source .env
   echo "Slack Token: ${SLACK_BOT_TOKEN:0:10}..."
   echo "Signing Secret: ${SLACK_SIGNING_SECRET:0:10}..."
   echo "Finnhub Key: ${FINNHUB_API_KEY:0:10}..."
   ```

### Step 2: Deploy Infrastructure

1. **Development Environment**:
   ```bash
   ./scripts/deploy-infrastructure.sh development us-east-1
   ```

2. **Staging Environment**:
   ```bash
   ./scripts/deploy-infrastructure.sh staging us-east-1
   ```

3. **Production Environment**:
   ```bash
   ./scripts/deploy-infrastructure.sh production us-east-1
   ```

The deployment script will:
- Validate prerequisites and environment variables
- Build the SAM application
- Deploy CloudFormation stack
- Configure DynamoDB tables
- Set up monitoring and logging
- Create CloudWatch dashboard

### Step 3: Configure Slack App URLs

After deployment, update your Slack app configuration with the API Gateway URLs:

1. **Get API Gateway URL**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name jain-trading-bot-development \
     --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
     --output text
   ```

2. **Update Slack App**:
   - Interactivity Request URL: `{API_URL}/slack/interactive`
   - Slash Command Request URL: `{API_URL}/slack/commands`
   - Event Subscriptions Request URL: `{API_URL}/slack/events`

### Step 4: Set Up Monitoring

1. **Deploy Monitoring**:
   ```bash
   ./scripts/setup-monitoring.sh development us-east-1 your-email@company.com
   ```

2. **Validate Deployment**:
   ```bash
   ./scripts/validate-infrastructure.sh development us-east-1
   ```

### Step 5: Test Deployment

1. **Health Check**:
   ```bash
   curl https://your-api-gateway-url/health
   ```

2. **Slack Integration Test**:
   - Go to your Slack workspace
   - Type `/trade` in an approved channel
   - Verify the modal opens correctly

## Environment-Specific Configurations

### Development Environment

- **Purpose**: Local development and testing
- **Features**:
  - Minimal monitoring
  - 30-day log retention
  - No encryption at rest
  - Basic error handling

### Staging Environment

- **Purpose**: Pre-production testing
- **Features**:
  - Enhanced monitoring
  - 90-day log retention
  - Basic encryption
  - Comprehensive error handling

### Production Environment

- **Purpose**: Live trading operations
- **Features**:
  - Full monitoring and alerting
  - 365-day log retention
  - KMS encryption at rest
  - Advanced security features
  - Point-in-time recovery for DynamoDB

## Security Considerations

### 1. Secrets Management

- Store sensitive values in AWS Systems Manager Parameter Store or AWS Secrets Manager
- Never commit secrets to version control
- Use IAM roles with least privilege access

### 2. Network Security

- API Gateway uses HTTPS only
- Lambda functions run in AWS managed VPC
- DynamoDB uses VPC endpoints where applicable

### 3. Data Protection

- Encryption at rest for DynamoDB (production)
- Encryption in transit for all communications
- Audit logging for all trading activities

### 4. Access Control

- Channel-based access restrictions
- Role-based user permissions
- API Gateway throttling and rate limiting

## Monitoring and Observability

### CloudWatch Dashboards

The deployment creates comprehensive dashboards:

1. **JainTradingBot-{Environment}**: Basic metrics
2. **JainTradingBot-{Environment}-Comprehensive**: Detailed monitoring

### Key Metrics to Monitor

1. **Lambda Function**:
   - Invocation count
   - Error rate
   - Duration
   - Throttles

2. **API Gateway**:
   - Request count
   - 4XX/5XX errors
   - Latency

3. **DynamoDB**:
   - Read/write capacity usage
   - Throttling events
   - Item counts

### Alerting

CloudWatch alarms are configured for:
- Lambda errors and throttles
- API Gateway 5XX errors
- DynamoDB throttling
- High latency issues

## Troubleshooting

### Common Issues

1. **Deployment Fails**:
   ```bash
   # Check CloudFormation events
   aws cloudformation describe-stack-events --stack-name jain-trading-bot-development
   
   # Check SAM build logs
   sam logs -n jain-trading-bot-development-lambda --stack-name jain-trading-bot-development
   ```

2. **Slack Integration Issues**:
   ```bash
   # Check Lambda logs
   aws logs tail /aws/lambda/jain-trading-bot-development-lambda --follow
   
   # Test API Gateway endpoints
   curl -X POST https://your-api-url/slack/events -d '{"challenge":"test"}'
   ```

3. **DynamoDB Issues**:
   ```bash
   # Check table status
   aws dynamodb describe-table --table-name jain-trading-bot-development-trades
   
   # Check for throttling
   aws cloudwatch get-metric-statistics \
     --namespace AWS/DynamoDB \
     --metric-name ReadThrottledEvents \
     --dimensions Name=TableName,Value=jain-trading-bot-development-trades \
     --start-time 2024-01-01T00:00:00Z \
     --end-time 2024-01-01T23:59:59Z \
     --period 3600 \
     --statistics Sum
   ```

### Log Analysis

Use CloudWatch Logs Insights for advanced log analysis:

```sql
-- Find recent errors
SOURCE '/aws/lambda/jain-trading-bot-development-lambda'
| fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 20

-- Analyze trade executions
SOURCE '/aws/lambda/jain-trading-bot-development-lambda'
| fields @timestamp, @message
| filter @message like /trade_executed/
| stats count() by bin(5m)

-- Performance analysis
SOURCE '/aws/lambda/jain-trading-bot-development-lambda'
| fields @timestamp, @duration, @message
| filter @duration > 10000
| sort @duration desc
```

## Maintenance and Updates

### Regular Maintenance

1. **Weekly**:
   - Review CloudWatch alarms
   - Check error logs
   - Monitor DynamoDB usage

2. **Monthly**:
   - Review and rotate secrets
   - Update dependencies
   - Analyze cost optimization opportunities

3. **Quarterly**:
   - Security audit
   - Performance optimization
   - Disaster recovery testing

### Updating the Application

1. **Code Updates**:
   ```bash
   # Deploy updated code
   ./scripts/deploy-infrastructure.sh development us-east-1
   
   # Validate deployment
   ./scripts/validate-infrastructure.sh development us-east-1
   ```

2. **Infrastructure Updates**:
   - Update `template.yaml`
   - Test in development first
   - Deploy to staging, then production

### Backup and Recovery

1. **DynamoDB**:
   - Point-in-time recovery (production)
   - On-demand backups
   - Cross-region replication (if needed)

2. **Configuration**:
   - Version control for all configuration
   - Infrastructure as Code (SAM templates)
   - Documented deployment procedures

## Cost Optimization

### Cost Monitoring

1. **AWS Cost Explorer**: Monitor spending by service
2. **CloudWatch Billing Alarms**: Set up cost alerts
3. **Resource Tagging**: Tag all resources for cost allocation

### Optimization Strategies

1. **Lambda**:
   - Right-size memory allocation
   - Optimize cold start performance
   - Use provisioned concurrency if needed

2. **DynamoDB**:
   - Use on-demand billing for variable workloads
   - Optimize partition key design
   - Implement data lifecycle policies

3. **API Gateway**:
   - Cache responses where appropriate
   - Implement request/response compression

## Support and Escalation

### Support Contacts

- **Development Team**: dev-team@jainglobal.com
- **Infrastructure Team**: infra-team@jainglobal.com
- **Security Team**: security@jainglobal.com

### Escalation Procedures

1. **P1 (Critical)**: Trading functionality down
   - Immediate notification to on-call engineer
   - Escalate to CTO within 15 minutes

2. **P2 (High)**: Performance degradation
   - Notification within 1 hour
   - Resolution target: 4 hours

3. **P3 (Medium)**: Non-critical issues
   - Notification within 24 hours
   - Resolution target: 48 hours

## Appendix

### A. Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `SLACK_BOT_TOKEN` | Yes | Slack Bot User OAuth Token | `xoxb-123...` |
| `SLACK_SIGNING_SECRET` | Yes | Slack App Signing Secret | `abc123...` |
| `FINNHUB_API_KEY` | Yes | Finnhub API Key for market data | `xyz789...` |
| `APPROVED_CHANNELS` | No | Comma-separated channel IDs | `C123,C456` |
| `BEDROCK_MODEL_ID` | No | Amazon Bedrock model ID | `anthropic.claude-3-sonnet...` |
| `LOG_LEVEL` | No | Application log level | `INFO` |

### B. AWS Resources Created

| Resource Type | Name Pattern | Purpose |
|---------------|--------------|---------|
| Lambda Function | `jain-trading-bot-{env}-lambda` | Main application |
| API Gateway | `jain-trading-bot-{env}-api` | HTTP endpoints |
| DynamoDB Table | `jain-trading-bot-{env}-trades` | Trade storage |
| DynamoDB Table | `jain-trading-bot-{env}-positions` | Position tracking |
| DynamoDB Table | `jain-trading-bot-{env}-channels` | Channel validation |
| CloudWatch Log Group | `/aws/lambda/jain-trading-bot-{env}-lambda` | Application logs |
| CloudWatch Dashboard | `JainTradingBot-{env}` | Monitoring |
| KMS Key | `jain-trading-bot-{env}-key` | Encryption (prod only) |

### C. API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/slack/events` | POST | Slack event subscriptions |
| `/slack/interactive` | POST | Interactive components |
| `/slack/commands` | POST | Slash commands |