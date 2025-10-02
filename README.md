# Slack Trading Bot for Jain Global

A sophisticated Slack bot that enables internal traders, analysts, and Portfolio Managers to simulate trades directly within Slack. This professional-grade "command center" replaces cumbersome mobile web applications with a fast, secure, mobile-first workflow for investment decisions.

## Key Features

- **Slash Command Trading**: Initiate trades with `/trade` command in approved private channels
- **AI-Powered Risk Analysis**: Real-time risk assessment using Amazon Bedrock Claude
- **Interactive Trade Widget**: Intuitive Block Kit modal for trade entry and confirmation
- **High-Risk Confirmation**: Enhanced security for high-risk trades with Portfolio Manager notifications
- **Portfolio Dashboard**: Personalized App Home tab with positions and P&L tracking
- **Role-Based Workflows**: Customized experiences for Research Analysts, Portfolio Managers, and Execution Traders
- **Market Data Integration**: Real-time pricing via Finnhub API
- **Secure Execution**: Proxy API integration with mock trading system
- **Comprehensive Audit Trail**: Full compliance logging and position tracking

## Architecture

- **Framework**: Python 3.11+ with Slack Bolt
- **Deployment**: AWS Serverless (Lambda, API Gateway, DynamoDB)
- **AI Service**: Amazon Bedrock (Claude model)
- **Market Data**: Finnhub API
- **Database**: DynamoDB with encryption at rest

## Project Documentation

This project follows Kiro's spec-driven development methodology with comprehensive documentation:

### 📋 [Requirements Document](.kiro/specs/slack-trading-bot/requirements.md)

Detailed user stories and acceptance criteria covering all 10 core requirements:

- Slash command initiation and channel restrictions
- Interactive trade widget and AI risk analysis
- High-risk confirmation workflows and secure execution
- Persistent data tracking and portfolio dashboard
- Role-based user workflows and market data integration

### 🏗️ [Design Document](.kiro/specs/slack-trading-bot/design.md)

Comprehensive technical architecture and implementation specifications:

- Serverless AWS architecture with security design
- Component interfaces and data models
- Error handling strategies and testing framework
- Code organization standards (300-400 lines per file minimum)

### ✅ [Implementation Tasks](.kiro/specs/slack-trading-bot/tasks.md)

Actionable coding tasks with comprehensive testing requirements:

- 10 major implementation phases with detailed subtasks
- Foundation setup through deployment and infrastructure
- Mandatory unit testing and security validation
- Requirements mapping for full traceability

## Getting Started

1. Review the [requirements document](.kiro/specs/slack-trading-bot/requirements.md) to understand the feature scope
2. Study the [design document](.kiro/specs/slack-trading-bot/design.md) for technical architecture
3. Begin implementation by opening [tasks.md](.kiro/specs/slack-trading-bot/tasks.md) and clicking "Start task" on any task item

## Development Workflow

- Each implementation file should contain 300-400+ lines of comprehensive code
- Run `npm run test` after implementing each layer/component
- All tests must pass before proceeding to the next implementation phase
- Follow test-driven development with mandatory unit testing

## Target Users

- **Research Analysts**: Rapid idea testing and proposal generation
- **Portfolio Managers**: Risk analysis and final trade decisions
- **Execution Traders**: Clear trade instructions and market execution
