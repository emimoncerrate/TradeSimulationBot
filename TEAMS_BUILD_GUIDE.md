# Microsoft Teams Trading Bot - Complete Build Guide

> **Complete technical specification for building a Microsoft Teams Trading Bot with Azure infrastructure, designed for VS Code development**

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [VS Code Setup](#vs-code-setup)
4. [Project Structure](#project-structure)
5. [Phase 1: Project Setup](#phase-1-vs-code-project-setup)
6. [Phase 2: Azure Infrastructure](#phase-2-azure-infrastructure-setup)
7. [Phase 3: Configuration & Models](#phase-3-configuration-and-models)
8. [Phase 4: Services Layer](#phase-4-services-layer)
9. [Phase 5: Bot Framework](#phase-5-bot-framework-implementation)
10. [Phase 6: Message Extensions](#phase-6-message-extensions)
11. [Phase 7: Teams Manifest](#phase-7-teams-app-manifest)
12. [Phase 8: Azure Functions](#phase-8-azure-functions-entry-point)
13. [Phase 9: Testing](#phase-9-testing-in-vs-code)
14. [Phase 10: Debugging](#phase-10-debugging-in-vs-code)
15. [Phase 11: Deployment](#phase-11-deployment-from-vs-code)
16. [Development Workflow](#development-workflow-in-vs-code)
17. [Deployment Checklist](#deployment-checklist)

---

## System Overview

A sophisticated **Microsoft Teams-based trading simulation bot** that enables traders, analysts, and Portfolio Managers to:
- ✅ Simulate trades directly within Teams
- ✅ Get AI-powered risk analysis
- ✅ Track comprehensive portfolios
- ✅ Integrate with Office 365

---

## Technology Stack

| Category | Technology |
|----------|------------|
| **Runtime** | Python 3.11+ |
| **Bot Framework** | Microsoft Bot Framework SDK (botbuilder-python) |
| **Web Framework** | Azure Functions + FastAPI |
| **Database** | Azure Cosmos DB (SQL API) |
| **AI/ML** | Azure OpenAI Service (GPT-4) |
| **Market Data** | Finnhub API |
| **Authentication** | Azure AD (Microsoft Entra ID) + OAuth 2.0 |
| **Deployment** | Azure Functions (serverless) |
| **Caching** | Azure Redis Cache |
| **Storage** | Azure Blob Storage |
| **Monitoring** | Application Insights |
| **Testing** | pytest, Bot Framework Emulator |
| **IDE** | Visual Studio Code |

---

## VS Code Setup

### Required Extensions

Create `.vscode/extensions.json`:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-azuretools.vscode-azurefunctions",
    "ms-vscode.azure-account",
    "ms-azuretools.vscode-cosmosdb",
    "ms-vscode.teams-toolkit",
    "redhat.vscode-yaml",
    "esbenp.prettier-vscode",
    "ms-vscode.test-adapter-converter"
  ]
}
```

### VS Code Settings

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "azureFunctions.deploySubpath": ".",
  "azureFunctions.scmDoBuildDuringDeployment": true,
  "azureFunctions.pythonVenv": "venv"
}
```

---

## Project Structure

```
TeamsTradingBot/
├── .vscode/
│   ├── launch.json              # Debug configurations
│   ├── settings.json            # VS Code settings
│   ├── tasks.json               # Build tasks
│   └── extensions.json          # Recommended extensions
│
├── bot/
│   ├── __init__.py
│   ├── teams_bot.py             # Main bot activity handler
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── trade_dialog.py
│   │   ├── portfolio_dialog.py
│   │   └── waterfall_dialog.py
│   ├── cards/
│   │   ├── __init__.py
│   │   ├── trade_card.py
│   │   ├── portfolio_card.py
│   │   ├── risk_card.py
│   │   ├── market_data_card.py
│   │   └── card_templates/
│   │       ├── trade_entry.json
│   │       ├── portfolio_summary.json
│   │       └── risk_analysis.json
│   └── middleware/
│       ├── __init__.py
│       ├── auth_middleware.py
│       ├── logging_middleware.py
│       └── telemetry_middleware.py
│
├── config/
│   ├── __init__.py
│   ├── settings.py              # Azure-focused configuration
│   └── teams_config.py
│
├── models/
│   ├── __init__.py
│   ├── user.py                  # User model with Azure AD
│   ├── trade.py                 # Trade model
│   ├── portfolio.py             # Portfolio models
│   └── risk_alert.py
│
├── services/
│   ├── __init__.py
│   ├── cosmos_db_service.py     # Azure Cosmos DB
│   ├── azure_openai_service.py  # GPT-4 risk analysis
│   ├── auth_service.py          # Azure AD auth
│   ├── graph_service.py         # Microsoft Graph API
│   ├── market_data_service.py   # Finnhub integration
│   ├── trading_api_service.py
│   ├── notification_service.py
│   └── service_container.py
│
├── extensions/
│   ├── __init__.py
│   ├── message_extension.py
│   ├── tab_app.py
│   └── meeting_extension.py
│
├── utils/
│   ├── __init__.py
│   ├── validators.py
│   ├── formatters.py
│   ├── adaptive_card_builder.py
│   └── async_helpers.py
│
├── tests/
│   ├── __init__.py
│   ├── test_bot.py
│   ├── test_cosmos_service.py
│   ├── test_auth_service.py
│   ├── test_adaptive_cards.py
│   └── integration/
│       ├── test_complete_flows.py
│       └── test_teams_scenarios.py
│
├── teams_manifest/
│   ├── manifest.json
│   ├── color.png                # 192x192
│   ├── outline.png              # 32x32
│   └── manifest.zip
│
├── bicep/                        # Infrastructure as Code
│   ├── main.bicep
│   ├── cosmos.bicep
│   ├── functions.bicep
│   └── openai.bicep
│
├── function_app.py               # Azure Functions entry point
├── host.json
├── local.settings.json
├── requirements.txt
├── .env.example
├── .gitignore
├── pytest.ini
└── README.md
```

---

## Phase 1: VS Code Project Setup

### 1.1 Initialize Project

Open VS Code terminal and run:

```bash
# Create project directory
mkdir TeamsTradingBot && cd TeamsTradingBot

# Open in VS Code
code .

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# Install VS Code extensions
code --install-extension ms-python.python
code --install-extension ms-azuretools.vscode-azurefunctions
code --install-extension ms-vscode.teams-toolkit
```

### 1.2 Debug Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Bot Framework",
      "type": "python",
      "request": "launch",
      "module": "aiohttp.web",
      "args": ["-H", "localhost", "-P", "3978", "app:init_func"],
      "envFile": "${workspaceFolder}/.env",
      "console": "integratedTerminal"
    },
    {
      "name": "Azure Functions: Bot",
      "type": "python",
      "request": "attach",
      "port": 9091,
      "preLaunchTask": "func: host start"
    },
    {
      "name": "Pytest: Current File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

### 1.3 Build Tasks

Create `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "func: host start",
      "type": "shell",
      "command": "func start",
      "problemMatcher": "$func-watch",
      "isBackground": true
    },
    {
      "label": "Run Tests",
      "type": "shell",
      "command": "pytest",
      "args": ["tests/", "-v", "--cov"],
      "group": "test"
    }
  ]
}
```

### 1.4 Install Dependencies

Create `requirements.txt`:

```txt
# Bot Framework
botbuilder-core==4.15.0
botbuilder-schema==4.15.0
botbuilder-integration-aiohttp==4.15.0
botframework-connector==4.15.0

# Azure Functions
azure-functions==1.18.0

# Azure Services
azure-cosmos==4.5.1
azure-identity==1.15.0
azure-keyvault-secrets==4.7.0
openai==1.6.1
azure-storage-blob==12.19.0

# Microsoft Graph
msgraph-core==1.0.0
msal==1.26.0

# Redis Cache
redis==5.0.1
aioredis==2.0.1

# Web Framework
fastapi==0.104.1
aiohttp==3.9.1
uvicorn==0.24.0

# Data Processing
pydantic==2.5.0
python-dateutil==2.8.2
python-dotenv==1.0.0

# HTTP Clients
httpx==0.25.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# Monitoring
applicationinsights==0.11.10
opencensus-ext-azure==1.1.13

# Utilities
tenacity==8.2.3
structlog==23.2.0
```

Install packages:

```bash
pip install -r requirements.txt
```

### 1.5 Environment Configuration

Create `.env`:

```bash
# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG_MODE=true
APP_VERSION=1.0.0

# Azure Functions
FUNCTIONS_WORKER_RUNTIME=python
FUNCTIONS_EXTENSION_VERSION=~4

# Microsoft Bot Framework
MICROSOFT_APP_ID=your-bot-app-id
MICROSOFT_APP_PASSWORD=your-bot-app-password
MICROSOFT_APP_TYPE=MultiTenant

# Azure AD Authentication
AZURE_AD_TENANT_ID=your-tenant-id
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_CLIENT_SECRET=your-client-secret

# Azure Cosmos DB
COSMOS_DB_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_DB_KEY=your-cosmos-key
COSMOS_DB_DATABASE=trading-bot
COSMOS_DB_CONTAINER_USERS=users
COSMOS_DB_CONTAINER_TRADES=trades
COSMOS_DB_CONTAINER_POSITIONS=positions

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-openai-key
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure Redis Cache
REDIS_HOST=your-cache.redis.cache.windows.net
REDIS_PORT=6380
REDIS_PASSWORD=your-redis-key
REDIS_SSL=true

# Azure Key Vault
KEY_VAULT_URL=https://your-keyvault.vault.azure.net/

# Market Data
FINNHUB_API_KEY=your-finnhub-key
FINNHUB_BASE_URL=https://finnhub.io/api/v1

# Trading Configuration
MOCK_EXECUTION_ENABLED=true
MAX_POSITION_SIZE=10000
MAX_TRADE_VALUE=1000000.0
SUPPORTED_SYMBOLS=AAPL,GOOGL,MSFT,AMZN,TSLA,META,NVDA,NFLX

# Application Insights
APPINSIGHTS_INSTRUMENTATION_KEY=your-insights-key

# Microsoft Graph
GRAPH_API_ENDPOINT=https://graph.microsoft.com/v1.0
```

---

## Phase 2: Azure Infrastructure Setup

### 2.1 Azure CLI Commands

**Create Resource Group:**

```bash
az group create --name rg-trading-bot --location eastus
```

**Provision Azure Cosmos DB:**

```bash
# Create Cosmos DB account
az cosmosdb create \
  --name trading-bot-cosmos \
  --resource-group rg-trading-bot \
  --default-consistency-level Session \
  --locations regionName=eastus

# Create database
az cosmosdb sql database create \
  --account-name trading-bot-cosmos \
  --resource-group rg-trading-bot \
  --name trading-bot

# Create users container
az cosmosdb sql container create \
  --account-name trading-bot-cosmos \
  --database-name trading-bot \
  --name users \
  --partition-key-path "/userId" \
  --throughput 400

# Create trades container
az cosmosdb sql container create \
  --account-name trading-bot-cosmos \
  --database-name trading-bot \
  --name trades \
  --partition-key-path "/userId" \
  --throughput 400

# Create positions container
az cosmosdb sql container create \
  --account-name trading-bot-cosmos \
  --database-name trading-bot \
  --name positions \
  --partition-key-path "/userId" \
  --throughput 400
```

**Provision Azure OpenAI:**

```bash
# Create OpenAI account
az cognitiveservices account create \
  --name trading-bot-openai \
  --resource-group rg-trading-bot \
  --kind OpenAI \
  --sku S0 \
  --location eastus

# Deploy GPT-4 model
az cognitiveservices account deployment create \
  --name trading-bot-openai \
  --resource-group rg-trading-bot \
  --deployment-name gpt-4 \
  --model-name gpt-4 \
  --model-version "0613" \
  --model-format OpenAI \
  --scale-settings-scale-type "Standard"
```

**Provision Azure Functions:**

```bash
# Create storage account
az storage account create \
  --name tradingbotstorage \
  --resource-group rg-trading-bot \
  --sku Standard_LRS

# Create Function App
az functionapp create \
  --name trading-bot-functions \
  --resource-group rg-trading-bot \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --storage-account tradingbotstorage
```

**Provision Redis Cache:**

```bash
az redis create \
  --name trading-bot-cache \
  --resource-group rg-trading-bot \
  --location eastus \
  --sku Basic \
  --vm-size c0
```

**Create Application Insights:**

```bash
az monitor app-insights component create \
  --app trading-bot-insights \
  --resource-group rg-trading-bot \
  --location eastus
```

### 2.2 Azure AD App Registration

**Steps:**

1. Go to Azure Portal → Azure AD → App registrations → New registration
2. **Name**: "Teams Trading Bot"
3. **Account types**: Multitenant
4. **Redirect URI**: `https://token.botframework.com/.auth/web/redirect`

**Configure API Permissions:**

- Microsoft Graph:
  - `User.Read` (Delegated)
  - `User.ReadBasic.All` (Delegated)
  - `Group.Read.All` (Application)
  - `Directory.Read.All` (Application)

**Create Client Secret:**

1. Go to Certificates & secrets
2. New client secret
3. Copy value for `.env` file

**Configure App Roles** (in Manifest):

```json
{
  "appRoles": [
    {
      "allowedMemberTypes": ["User"],
      "displayName": "Research Analyst",
      "id": "00000000-0000-0000-0000-000000000001",
      "isEnabled": true,
      "description": "Can execute trades and view risk analysis",
      "value": "Analyst"
    },
    {
      "allowedMemberTypes": ["User"],
      "displayName": "Portfolio Manager",
      "id": "00000000-0000-0000-0000-000000000002",
      "isEnabled": true,
      "description": "Full oversight and approval authority",
      "value": "PortfolioManager"
    },
    {
      "allowedMemberTypes": ["User"],
      "displayName": "Execution Trader",
      "id": "00000000-0000-0000-0000-000000000003",
      "isEnabled": true,
      "description": "Streamlined trade execution",
      "value": "Trader"
    }
  ]
}
```

---

## Development Workflow in VS Code

### Daily Development

1. **Open project** in VS Code
2. **Activate venv**: Terminal → `source venv/bin/activate`
3. **Run tests**: Testing panel (flask icon)
4. **Start debugging**: Press F5
5. **Make changes**: Live reload enabled
6. **Commit**: Source Control panel (Ctrl+Shift+G)
7. **Push**: To Git repository

### Testing Flow

1. Write tests in `tests/`
2. Right-click test → "Run Test"
3. Or: Testing panel → Play button
4. View coverage: `pytest --cov`
5. Fix failures
6. Commit when green ✅

### Debugging Flow

1. Set breakpoints (click left margin)
2. Press F5 to start debugger
3. Send message in Bot Framework Emulator
4. Step through code (F10=over, F11=into)
5. Inspect variables in Debug panel
6. Modify and hot-reload

---

## Key Teams Features

### ✨ 1. Adaptive Cards with Refresh
- Card updates without reposting
- Live market data on cards
- Dynamic risk indicators

### ✨ 2. Task Modules
- Modal dialogs for complex workflows
- Multi-step trade entry
- Portfolio detail views

### ✨ 3. Activity Feed
- Trade execution notifications
- Risk alerts
- Approval requests

### ✨ 4. Message Extensions
- Stock symbol search
- Quick trade actions
- Link unfurling for portfolios

### ✨ 5. Tabs
- Custom portfolio dashboard tab
- Analytics and charts
- Trade history view

### ✨ 6. Meeting Extensions
- Show portfolio during meetings
- Collaborative trade decisions
- Real-time market data in meetings

---

## VS Code Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **F5** | Start debugging |
| **Ctrl+Shift+P** | Command palette |
| **Ctrl+`** | Toggle terminal |
| **Ctrl+Shift+G** | Source control |
| **Ctrl+Shift+E** | Explorer |
| **Ctrl+Shift+D** | Debug panel |
| **Ctrl+Shift+X** | Extensions |
| **Ctrl+Shift+F** | Search |
| **F10** | Step over |
| **F11** | Step into |

---

## Deployment Checklist

### Azure Resources
- [ ] Resource Group created
- [ ] Cosmos DB provisioned with containers
- [ ] Azure OpenAI deployed with GPT-4 model
- [ ] Azure Functions created
- [ ] Redis Cache provisioned
- [ ] Application Insights configured
- [ ] Key Vault set up

### Azure AD
- [ ] App registration created
- [ ] API permissions configured
- [ ] Client secret generated
- [ ] App roles defined in manifest

### Bot Configuration
- [ ] Bot registered in Bot Framework
- [ ] Environment variables configured in `.env`
- [ ] Teams manifest created
- [ ] App icons prepared (192x192 & 32x32)

### Development
- [ ] VS Code extensions installed
- [ ] Virtual environment activated
- [ ] Dependencies installed
- [ ] Tests passing
- [ ] Bot tested in emulator

### Deployment
- [ ] Function app deployed to Azure
- [ ] Teams app uploaded to Admin Center
- [ ] Users assigned app roles
- [ ] Monitoring dashboards created
- [ ] Documentation complete

---

## Next Steps

1. **Set up Azure infrastructure** using CLI commands above
2. **Create project structure** following the layout
3. **Implement configuration** (Phase 3)
4. **Build services layer** (Phase 4)
5. **Create bot handlers** (Phase 5)
6. **Test locally** with Bot Framework Emulator
7. **Deploy to Azure** using VS Code extension
8. **Install in Teams** and test

---

## Support & Resources

- **Bot Framework Docs**: https://docs.microsoft.com/en-us/azure/bot-service/
- **Teams Platform**: https://docs.microsoft.com/en-us/microsoftteams/platform/
- **Azure OpenAI**: https://learn.microsoft.com/en-us/azure/ai-services/openai/
- **Cosmos DB**: https://docs.microsoft.com/en-us/azure/cosmos-db/
- **Bot Framework Emulator**: https://github.com/Microsoft/BotFramework-Emulator

---

**Built with ❤️ for Microsoft Teams**

