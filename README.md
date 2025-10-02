# Jain Global Slack Trading Bot

A sophisticated Slack-based trading simulation bot for Jain Global investment management firm. This bot enables traders, analysts, and Portfolio Managers to simulate trades directly within Slack with AI-powered risk analysis and comprehensive portfolio tracking.

## 🚀 Features

- **Slash Command Trading**: Initiate trades with `/trade` command
- **AI Risk Analysis**: Amazon Bedrock Claude integration for trade risk assessment
- **Portfolio Dashboard**: Real-time portfolio tracking in Slack App Home
- **Role-Based Access**: Different workflows for Research Analysts, Portfolio Managers, and Execution Traders
- **Market Data Integration**: Real-time market data from Finnhub API
- **Secure Architecture**: Channel restrictions, audit logging, and compliance features
- **Serverless Deployment**: AWS Lambda with DynamoDB and API Gateway

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Slack Client  │───▶│   API Gateway   │───▶│  Lambda Function │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐             │
                       │   Amazon        │◀────────────┤
                       │   Bedrock       │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │   DynamoDB      │◀────────────┤
                       │   Tables        │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │   Finnhub API   │◀────────────┘
                       └─────────────────┘
```

## 📋 Prerequisites

- Python 3.11+
- Docker and Docker Compose
- AWS CLI configured
- AWS SAM CLI
- Slack workspace with admin permissions

## 🛠️ Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd slack-trading-bot
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Required variables:
# - SLACK_BOT_TOKEN
# - SLACK_SIGNING_SECRET  
# - FINNHUB_API_KEY
# - APPROVED_CHANNELS
```

### 3. Local Development with Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f slack-trading-bot

# Access services:
# - Main App: http://localhost:3000
# - DynamoDB Admin: http://localhost:8001
# - Redis Commander: http://localhost:8002
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3001
```

### 4. Local Development without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## 🚀 Deployment

### AWS Lambda Deployment

```bash
# Build and deploy to development
./scripts/deploy-lambda.sh deploy --environment development --guided

# Deploy to production
./scripts/deploy-lambda.sh deploy --environment production --s3-bucket your-deployment-bucket
```

### Docker Container Deployment

```bash
# Build production image
./scripts/docker-build.sh production --tag v1.0.0

# Build and push to ECR
./scripts/docker-build.sh lambda --registry 123456789012.dkr.ecr.us-east-1.amazonaws.com --push
```

## 📁 Project Structure

```
├── app.py                 # Main application entry point
├── config/
│   └── settings.py        # Configuration management
├── listeners/
│   ├── commands.py        # Slash command handlers
│   ├── actions.py         # Interactive component handlers
│   └── events.py          # Slack event handlers
├── services/              # Business logic services
├── models/                # Data models
├── ui/                    # Slack UI components
├── utils/                 # Utility functions
├── scripts/               # Deployment and build scripts
├── template.yaml          # AWS SAM template
├── docker-compose.yml     # Local development environment
└── requirements.txt       # Python dependencies
```

## 🔧 Configuration

### Environment Variables

Key environment variables (see `.env.example` for complete list):

```bash
# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG_MODE=true

# Slack
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-secret
SLACK_APP_TOKEN=xapp-your-token  # For Socket Mode

# AWS
AWS_REGION=us-east-1
DYNAMODB_TABLE_PREFIX=jain-trading-bot

# Market Data
FINNHUB_API_KEY=your-api-key

# Security
APPROVED_CHANNELS=C1234567890,C0987654321
```

### Slack App Configuration

1. Create a new Slack app at https://api.slack.com/apps
2. Configure OAuth scopes:
   - `chat:write`
   - `commands`
   - `im:history`
   - `channels:read`
   - `users:read`
3. Add slash command: `/trade`
4. Enable Interactive Components
5. Configure App Home tab
6. Install app to workspace

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_config.py -v

# Run tests in Docker
docker-compose run --rm slack-trading-bot pytest
```

## 📊 Monitoring

### Local Development

- **Application Logs**: `docker-compose logs -f slack-trading-bot`
- **Prometheus Metrics**: http://localhost:9090
- **Grafana Dashboard**: http://localhost:3001 (admin/admin)
- **Jaeger Tracing**: http://localhost:16686

### Production

- **CloudWatch Logs**: `/aws/lambda/jain-trading-bot-lambda`
- **CloudWatch Metrics**: Custom metrics namespace `JainTradingBot`
- **X-Ray Tracing**: Enabled for Lambda function

## 🔒 Security

- **Channel Restrictions**: Bot only works in approved private channels
- **Role-Based Access**: Different permissions for analysts, PMs, and traders
- **Audit Logging**: All trading activities logged for compliance
- **Data Encryption**: DynamoDB encryption at rest with KMS
- **Network Security**: VPC deployment with security groups

## 📚 API Documentation

### Slack Commands

- `/trade` - Initiate a new trade simulation

### Interactive Components

- Trade Modal - Input trade parameters
- Risk Analysis - AI-powered risk assessment
- Portfolio Dashboard - View positions and P&L

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes and add tests
4. Run tests: `pytest`
5. Commit changes: `git commit -am 'Add new feature'`
6. Push to branch: `git push origin feature/new-feature`
7. Submit a Pull Request

## 📄 License

This project is proprietary software owned by Jain Global. All rights reserved.

## 🆘 Support

For support and questions:

- Internal Documentation: [Confluence Link]
- Slack Channel: #trading-bot-support
- Email: trading-tech@jainglobal.com

## 🔄 Changelog

### v1.0.0 (Current)
- Initial release with core trading functionality
- AI-powered risk analysis
- Portfolio dashboard
- AWS Lambda deployment

---

**Note**: This is the foundation implementation. Additional features will be added in subsequent tasks according to the implementation plan.