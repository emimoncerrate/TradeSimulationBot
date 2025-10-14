# Alpaca Trading Integration Setup Guide

This guide walks you through setting up real trading integration with Alpaca Markets.

## 🚀 Quick Start

### 1. Get Alpaca API Keys

1. Sign up for a free account at [Alpaca Markets](https://alpaca.markets)
2. Navigate to your Paper Trading dashboard
3. Go to "API Keys" section
4. Click "Generate New Key"
5. **Important**: Save both the Key ID and Secret Key securely
   - ⚠️ **Never commit these to version control!**
   - ⚠️ **Never share these keys publicly!**

### 2. Configure Environment Variables

Add these variables to your `.env` file:

```bash
# =============================================================================
# Alpaca Trading Platform Configuration
# =============================================================================

# Enable/disable Alpaca integration
ALPACA_ENABLED=true  # Set to true when you have API keys

# API Credentials
ALPACA_API_KEY=your-alpaca-api-key-here
ALPACA_SECRET_KEY=your-alpaca-secret-key-here

# Trading Environment
# Paper trading (recommended for testing):
ALPACA_BASE_URL=https://paper-api.alpaca.markets
ALPACA_PAPER_TRADING=true

# Real trading configuration
USE_REAL_TRADING=true  # Set to true to enable real trading via Alpaca
```

### 3. Install Dependencies

```bash
# Install the Alpaca Python SDK
pip install alpaca-trade-api==3.1.1

# Or install all dependencies
pip install -r requirements.txt
```

### 4. Test the Integration

Run the test script to verify everything is working:

```bash
python test_alpaca_integration.py
```

This will:
- ✅ Test API connection
- ✅ Verify account access
- ✅ Check current positions
- ✅ Validate configuration
- ✅ Optionally execute a test trade

### 5. Enable Real Trading

Once tests pass, your Slack bot will route trades to Alpaca:

```bash
# In your .env file:
USE_REAL_TRADING=true
ALPACA_ENABLED=true
```

Restart your application, and trades initiated from Slack will now be executed on Alpaca!

## 📋 Complete Environment Variables

Here's the complete list of Alpaca-related environment variables:

```bash
# Enable Alpaca
ALPACA_ENABLED=false          # true to enable, false to disable

# API Credentials
ALPACA_API_KEY=               # Your Alpaca API Key ID
ALPACA_SECRET_KEY=            # Your Alpaca Secret Key

# Trading Environment
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Paper trading
# ALPACA_BASE_URL=https://api.alpaca.markets      # Live trading

ALPACA_PAPER_TRADING=true     # true for paper, false for live

# Main trading flag
USE_REAL_TRADING=false        # true to route trades to Alpaca
```

## 🔄 How It Works

### Trade Flow with Alpaca Integration

```
User in Slack → /trade command
    ↓
Trade Modal (collect details)
    ↓
User submits: Symbol, Quantity, Type
    ↓
TradingAPIService.execute_trade()
    ↓
├─ IF USE_REAL_TRADING=true AND ALPACA_ENABLED=true:
│     ↓
│  AlpacaTradingService.execute_trade()
│     ↓
│  Alpaca API (Paper or Live)
│     ↓
│  Real order execution
│
└─ ELSE:
      ↓
   Mock execution (simulation)
      ↓
   Simulated fills
```

### Configuration States

| USE_REAL_TRADING | ALPACA_ENABLED | Result |
|-----------------|----------------|--------|
| `false` | `false` | Mock trading (simulation) |
| `false` | `true` | Mock trading (Alpaca ignored) |
| `true` | `false` | Mock trading (fallback) |
| `true` | `true` | **Real trading via Alpaca** ✅ |

## 🧪 Testing Strategy

### Phase 1: Connection Testing
```bash
python test_alpaca_integration.py
```
- Verify API credentials
- Check account access
- View current positions

### Phase 2: Paper Trading
```bash
# In .env:
ALPACA_PAPER_TRADING=true
ALPACA_BASE_URL=https://paper-api.alpaca.markets
USE_REAL_TRADING=true
ALPACA_ENABLED=true
```
- Execute small test trades (1 share)
- Verify execution reports
- Check position updates
- Test in Slack with `/trade` command

### Phase 3: Live Trading (When Ready)
```bash
# In .env:
ALPACA_PAPER_TRADING=false
ALPACA_BASE_URL=https://api.alpaca.markets
```
- ⚠️ **Use extreme caution!**
- Start with very small quantities
- Fund account appropriately
- Monitor executions closely

## 🔒 Security Best Practices

### API Key Security
1. ✅ Store keys in `.env` file (never in code)
2. ✅ Add `.env` to `.gitignore`
3. ✅ Use separate keys for paper and live trading
4. ✅ Rotate keys periodically
5. ✅ Revoke unused keys immediately

### Trading Safety
1. ✅ Start with paper trading
2. ✅ Set position limits in configuration
3. ✅ Implement approval workflows for large trades
4. ✅ Enable audit logging
5. ✅ Monitor executions in real-time

### Configuration Management
```bash
# Development
ENVIRONMENT=development
USE_REAL_TRADING=false

# Staging (Paper Trading)
ENVIRONMENT=staging
USE_REAL_TRADING=true
ALPACA_PAPER_TRADING=true

# Production (Live Trading)
ENVIRONMENT=production
USE_REAL_TRADING=true
ALPACA_PAPER_TRADING=false
```

## 📊 Monitoring and Validation

### Check Trading Status

```python
# In your application
from config.settings import get_config

config = get_config()
print(f"Real Trading: {config.trading.use_real_trading}")
print(f"Alpaca Enabled: {config.alpaca.enabled}")
print(f"Paper Trading: {config.alpaca.paper_trading}")
```

### View Account Information

```python
from services.alpaca_trading import get_alpaca_trading_service

service = await get_alpaca_trading_service()
account = await service.get_account_info()
print(f"Buying Power: ${account['buying_power']:,.2f}")
```

### Check Positions

```python
positions = await service.get_positions()
for pos in positions:
    print(f"{pos['symbol']}: {pos['quantity']} shares")
```

## 🚨 Troubleshooting

### Common Issues

**Problem**: `Authentication failed`
- **Solution**: Verify API keys are correct and active
- Check you're using the right URL for paper/live trading

**Problem**: `Insufficient buying power`
- **Solution**: Paper accounts start with $100,000
- Check current balance with account info test

**Problem**: `Symbol not tradable`
- **Solution**: Verify symbol is valid
- Some symbols have trading restrictions

**Problem**: `Market is closed`
- **Solution**: Orders will queue until market opens
- Or use extended hours trading (if configured)

### Debug Mode

Enable detailed logging:

```bash
LOG_LEVEL=DEBUG
DEBUG_MODE=true
```

View logs for Alpaca interactions:
```bash
tail -f jain_global_slack_trading_bot.log | grep -i alpaca
```

## 📚 API Documentation

- [Alpaca API Docs](https://alpaca.markets/docs/api-documentation/)
- [Python SDK](https://github.com/alpacahq/alpaca-trade-api-python)
- [Paper Trading](https://alpaca.markets/docs/trading/paper-trading/)

## 🆘 Support

### Issues with Integration
1. Run the test script: `python test_alpaca_integration.py`
2. Check logs for error messages
3. Verify all environment variables are set
4. Ensure API keys are valid and not expired

### Alpaca Support
- [Alpaca Community Forum](https://forum.alpaca.markets/)
- [Alpaca Support](https://alpaca.markets/support)
- Email: support@alpaca.markets

### Application Support
- Check logs: `jain_global_slack_trading_bot.log`
- Review configuration: Run Test 5 in test script
- Contact internal support team

## ✅ Pre-Launch Checklist

Before enabling live trading, verify:

- [ ] Paper trading tested successfully
- [ ] Test script passes all tests
- [ ] API keys are for correct environment (paper/live)
- [ ] Position limits configured appropriately
- [ ] Approval workflows in place for large trades
- [ ] Monitoring and alerting enabled
- [ ] Audit logging active
- [ ] Team trained on the system
- [ ] Rollback plan documented
- [ ] Support team notified

## 🎯 Next Steps

1. ✅ Complete setup following this guide
2. ✅ Run integration tests
3. ✅ Test with paper trading
4. ✅ Validate in Slack with `/trade` command
5. ✅ Monitor several paper trades
6. ✅ Review with team before going live

---

**Remember**: Start with paper trading, test thoroughly, and only move to live trading when you're confident everything works correctly!

