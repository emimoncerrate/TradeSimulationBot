# Jain Global Slack Trading Bot - Deployment & Configuration

## Overview

This document provides comprehensive instructions for deploying and configuring the Jain Global Slack Trading Bot. The system includes AWS infrastructure, Slack app configuration, security settings, and monitoring capabilities.

## Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- SAM CLI installed
- Docker installed (for local testing)
- Slack workspace admin access

### Environment Variables
Create a `.env` file with:
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
FINNHUB_API_KEY=your-finnhub-api-key
APPROVED_CHANNELS=C1234567890,C0987654321
```

### One-Command Deployment
```bash
# Deploy complete system
./scripts/deploy-complete-system.sh development us-east-1 your-email@company.com
```

## Deployment Scripts

### Infrastructure Deployment
```bash
# Deploy AWS infrastructure only
./scripts/deploy-infrastructure.sh [environment] [region]

# Examples
./scripts/deploy-infrastructure.sh development us-east-1
./scripts/deploy-infrastructure.sh production us-west-2
```

### Monitoring Setup
```bash
# Set up monitoring and alerting
./scripts/setup-monitoring.sh [environment] [region] [email]

# Example
./scripts/setup-monitoring.sh production us-east-1 alerts@jainglobal.com
```

### Security Configuration
```bash
# Configure security settings
./scripts/setup-slack-security.sh [environment] [region]

# Example
./scripts/setup-slack-security.sh production us-east-1
```

### Slack App Configuration
```bash
# Generate Slack app configuration files
./scripts/configure-slack-app.sh [environment] [api-gateway-url]

# Example
./scripts/configure-slack-app.sh development https://abc123.execute-api.us-east-1.amazonaws.com/development
```

## Validation Scripts

### Infrastructure Validation
```bash
# Validate AWS infrastructure
./scripts/validate-infrastructure.sh [environment] [region]

# Example
./scripts/validate-infrastructure.sh development us-east-1
```

### Security Validation
```bash
# Validate security configuration
./scripts/validate-security-config.sh [environment] [region]

# Example
./scripts/validate-security-config.sh production us-east-1
```

### Slack Configuration Validation
```bash
# Validate Slack app configuration
./scripts/validate-slack-config.sh [environment] [api-gateway-url]

# Example
./scripts/validate-slack-config.sh development https://abc123.execute-api.us-east-1.amazonaws.com/development
```

## Configuration Files

### Generated Configuration Files

#### Slack Configuration
- `config/slack/app-manifest-{environment}.json` - Slack app manifest
- `config/slack/setup-instructions-{environment}.md` - Step-by-step setup guide
- `config/slack/workspace-installation-guide.md` - Workspace installation procedures

#### Security Configuration
- `config/security/slack-bot-iam-policy.json` - IAM policy for Lambda function
- `config/security/security-config-{environment}.json` - Environment-specific security settings
- `config/security/approved-channels-template.json` - Channel security template
- `config/security/user-roles-{environment}.json` - User roles and permissions
- `config/security/security-monitoring-{environment}.json` - Security monitoring configuration
- `config/security/compliance-config-{environment}.json` - Compliance settings

#### Documentation
- `docs/deployment-guide.md` - Comprehensive deployment guide
- `deployment-summary-{environment}.md` - Deployment summary (generated after deployment)

## Environment-Specific Configurations

### Development Environment
- **Purpose**: Testing and development
- **Features**: Basic monitoring, 30-day log retention, no encryption
- **Security**: Medium security level, development-friendly settings

### Staging Environment
- **Purpose**: Pre-production testing
- **Features**: Enhanced monitoring, 90-day log retention, basic encryption
- **Security**: High security level, production-like settings

### Production Environment
- **Purpose**: Live trading operations
- **Features**: Full monitoring, 365-day log retention, KMS encryption
- **Security**: Maximum security level, compliance-ready settings

## Slack App Setup Process

### 1. Create Slack App
1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Create new app using the generated manifest file
3. Configure OAuth scopes and permissions

### 2. Configure Endpoints
Set these URLs in your Slack app:
- **Events**: `{API_GATEWAY_URL}/slack/events`
- **Interactive**: `{API_GATEWAY_URL}/slack/interactive`
- **Commands**: `{API_GATEWAY_URL}/slack/commands`

### 3. Install to Workspace
1. Install app to workspace
2. Copy Bot User OAuth Token
3. Update environment variables
4. Redeploy infrastructure

### 4. Configure Channels
1. Create private channels for trading
2. Add team members to channels
3. Invite bot to channels
4. Update approved channels list

## Security Features

### Access Control
- Channel-based restrictions (private channels only)
- Role-based user permissions
- API Gateway throttling and rate limiting

### Data Protection
- Encryption at rest (production)
- Encryption in transit (all environments)
- Audit logging for all activities

### Monitoring
- Real-time security alerts
- Compliance monitoring
- Performance monitoring
- Error tracking and alerting

### User Roles
- **Research Analyst**: Create proposals, view analysis
- **Portfolio Manager**: Approve trades, comprehensive access
- **Execution Trader**: Execute trades, view status
- **Compliance Officer**: Audit access, read-only

## Monitoring and Observability

### CloudWatch Dashboards
- **JainTradingBot-{Environment}**: Basic metrics
- **JainTradingBot-{Environment}-Comprehensive**: Detailed monitoring

### Key Metrics
- Lambda function performance (invocations, errors, duration)
- API Gateway metrics (requests, errors, latency)
- DynamoDB usage (capacity, throttling, item counts)

### Alerting
- Lambda errors and throttles
- API Gateway 5XX errors
- DynamoDB throttling
- Security events

### Log Analysis
Use CloudWatch Logs Insights for advanced analysis:
```sql
-- Recent errors
SOURCE '/aws/lambda/jain-trading-bot-development-lambda'
| fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc

-- Trade executions
SOURCE '/aws/lambda/jain-trading-bot-development-lambda'
| fields @timestamp, @message
| filter @message like /trade_executed/
| stats count() by bin(5m)
```

## Troubleshooting

### Common Issues

#### Deployment Failures
```bash
# Check CloudFormation events
aws cloudformation describe-stack-events --stack-name jain-trading-bot-development

# Check Lambda logs
aws logs tail /aws/lambda/jain-trading-bot-development-lambda --follow
```

#### Slack Integration Issues
```bash
# Test API endpoints
curl https://your-api-url/health
curl -X POST https://your-api-url/slack/events -d '{"challenge":"test"}'

# Check Slack app configuration
./scripts/validate-slack-config.sh development https://your-api-url
```

#### Permission Issues
```bash
# Validate IAM permissions
aws iam get-role --role-name your-lambda-role
aws iam list-attached-role-policies --role-name your-lambda-role
```

### Log Locations
- **Lambda Logs**: `/aws/lambda/jain-trading-bot-{environment}-lambda`
- **API Gateway Logs**: `/aws/apigateway/jain-trading-bot-{environment}-api`
- **Deployment Logs**: `deployment-{environment}-{timestamp}.log`

## Maintenance

### Regular Tasks
- **Weekly**: Review error logs and performance metrics
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Security audit and compliance review

### Updates and Patches
1. Test in development environment
2. Deploy to staging for validation
3. Schedule production deployment
4. Monitor post-deployment metrics

### Backup and Recovery
- DynamoDB point-in-time recovery (production)
- Infrastructure as Code (SAM templates)
- Configuration version control

## Cost Optimization

### Monitoring Costs
- Use AWS Cost Explorer for spending analysis
- Set up billing alarms
- Tag resources for cost allocation

### Optimization Strategies
- Right-size Lambda memory allocation
- Use DynamoDB on-demand billing
- Implement API Gateway caching
- Optimize log retention periods

## Support and Escalation

### Support Contacts
- **Development**: dev-team@jainglobal.com
- **Infrastructure**: infra-team@jainglobal.com
- **Security**: security@jainglobal.com

### Escalation Procedures
- **P1 (Critical)**: Trading functionality down - immediate escalation
- **P2 (High)**: Performance issues - 1-hour response
- **P3 (Medium)**: Non-critical issues - 24-hour response

## Compliance and Governance

### Regulatory Requirements
- SOX compliance for financial data
- FINRA regulations for trading activities
- GDPR/CCPA for data protection

### Data Retention
- Trade records: 7 years
- Communication records: 3 years
- Audit logs: 7 years
- System logs: 1 year

### Audit Trail
- All trading activities logged
- User access tracking
- System changes documented
- Regular compliance reports

## Getting Help

### Documentation
- [Deployment Guide](docs/deployment-guide.md) - Comprehensive deployment instructions
- [API Documentation](docs/api-documentation.md) - API reference
- [User Guide](docs/user-guide.md) - End-user instructions

### Validation Tools
- Infrastructure validation: `./scripts/validate-infrastructure.sh`
- Security validation: `./scripts/validate-security-config.sh`
- Slack configuration validation: `./scripts/validate-slack-config.sh`

### Monitoring Resources
- CloudWatch Dashboards
- CloudWatch Logs Insights
- AWS X-Ray tracing
- Custom metrics and alarms

---

**Last Updated**: $(date)  
**Version**: 1.0  
**Environment**: All environments supported