# 📁 Project Structure

## 🗂️ **Root Directory Layout**

```
TradeSimulationBot/
├── 📄 app.py                    # Main application entry point
├── 📄 requirements.txt          # Python dependencies
├── 📄 .env                      # Environment configuration (local)
├── 📄 .env.example              # Environment template
├── 📄 README.md                 # Main project documentation
├── 📄 docker-compose.yml        # Docker services configuration
├── 📄 Dockerfile                # Container build instructions
├── 📄 template.yaml             # AWS CloudFormation template
├── 📄 .gitignore                # Git ignore rules
├── 📄 .dockerignore             # Docker ignore rules
│
├── 📁 config/                   # Configuration management
│   ├── settings.py              # Application settings
│   └── __init__.py
│
├── 📁 services/                 # Core business logic services
│   ├── auth.py                  # Authentication service
│   ├── database.py              # Database operations
│   ├── market_data.py           # Market data integration
│   ├── alpaca_service.py        # Alpaca paper trading
│   ├── trading_api.py           # Trading execution logic
│   ├── risk_analysis.py         # Risk management
│   ├── service_container.py     # Dependency injection
│   └── __init__.py
│
├── 📁 models/                   # Data models and schemas
│   ├── user.py                  # User model and permissions
│   ├── trade.py                 # Trade execution models
│   ├── portfolio.py             # Portfolio tracking
│   └── __init__.py
│
├── 📁 listeners/                # Slack event handlers
│   ├── commands.py              # Slash command handlers
│   ├── actions.py               # Interactive action handlers
│   ├── events.py                # Slack event listeners
│   ├── enhanced_trade_command.py # Advanced trade modal
│   ├── enhanced_market_actions.py # Market data interactions
│   └── __init__.py
│
├── 📁 utils/                    # Utility functions
│   ├── formatters.py            # Data formatting helpers
│   ├── validators.py            # Input validation
│   ├── decorators.py            # Common decorators
│   └── __init__.py
│
├── 📁 ui/                       # User interface components
│   ├── modals.py                # Slack modal builders
│   ├── blocks.py                # Slack block kit components
│   └── __init__.py
│
├── 📁 scripts/                  # Setup and maintenance scripts
│   ├── create_dynamodb_tables.py # Database table creation
│   ├── setup_local_dynamodb.sh   # DynamoDB container setup
│   └── (other deployment scripts)
│
├── 📁 tests/                    # Test suite
│   ├── test_auth_service.py     # Authentication tests
│   ├── test_database_service.py # Database tests
│   ├── test_integration.py      # Integration tests
│   └── (other test files)
│
├── 📁 tools/                    # Development utilities
│   ├── view_database.py         # Database viewer
│   ├── demo_enhanced_trade.py   # Demo scripts
│   └── (other utility tools)
│
├── 📁 docs/                     # Documentation
│   ├── setup/
│   │   └── SETUP_LOG.md         # Complete setup guide
│   ├── fixes/
│   │   ├── AUTHENTICATION_FIX_SUMMARY.md
│   │   ├── COMMAND_REGISTRATION_FIX.md
│   │   └── (other fix documentation)
│   ├── guides/
│   │   ├── README-Deployment.md
│   │   ├── README-Docker.md
│   │   └── (other guides)
│   └── kiro_summary_log.md
│
├── 📁 logs/                     # Application logs
│   └── (log files)
│
└── 📁 .kiro/                    # Kiro IDE configuration
    └── (IDE settings)
```

## 🎯 **Key Components**

### **Core Application**

- **`app.py`** - Main entry point, starts the Slack bot
- **`config/`** - Centralized configuration management
- **`services/`** - Business logic and external integrations

### **Slack Integration**

- **`listeners/`** - Handles all Slack interactions
- **`ui/`** - Slack interface components (modals, blocks)

### **Data Layer**

- **`models/`** - Data structures and business entities
- **`services/database.py`** - Database operations and persistence

### **Trading Features**

- **`services/alpaca_service.py`** - Paper trading integration
- **`services/market_data.py`** - Real-time market data
- **`services/trading_api.py`** - Trade execution logic

### **Development & Deployment**

- **`scripts/`** - Setup and maintenance automation
- **`tests/`** - Comprehensive test suite
- **`tools/`** - Development utilities
- **`docs/`** - Complete documentation

## 🚀 **Quick Start Files**

| File                              | Purpose                |
| --------------------------------- | ---------------------- |
| `app.py`                          | Start the bot          |
| `.env`                            | Configure environment  |
| `docs/setup/SETUP_LOG.md`         | Complete setup guide   |
| `tools/view_database.py`          | View database contents |
| `scripts/setup_local_dynamodb.sh` | Setup local database   |

## 📊 **File Organization Principles**

1. **Separation of Concerns** - Each folder has a specific purpose
2. **Logical Grouping** - Related files are grouped together
3. **Clear Naming** - File names indicate their function
4. **Documentation** - All major components are documented
5. **Development Tools** - Utilities are separated from core code

## 🔧 **Development Workflow**

1. **Start Here**: `docs/setup/SETUP_LOG.md`
2. **Configure**: Edit `.env` file
3. **Run Setup**: Execute scripts in `scripts/`
4. **Start Bot**: `python app.py`
5. **Test**: Use files in `tests/`
6. **Debug**: Check `logs/` and use `tools/`

This structure supports both development and production deployment while keeping the codebase organized and maintainable.
