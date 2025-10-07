# 🚀 Alpaca Paper Trading Integration - Setup Guide

## ✅ What's Been Completed

### 1. **Alpaca Trade API Installed** ✅
The `alpaca-trade-api` package is installed in your virtual environment.

### 2. **Configuration Added** ✅
Your `.env` file now has Alpaca configuration (at the bottom):
```bash
ALPACA_PAPER_API_KEY=YOUR_PAPER_API_KEY_HERE
ALPACA_PAPER_SECRET_KEY=YOUR_PAPER_SECRET_KEY_HERE
ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets
ALPACA_PAPER_ENABLED=true
ALPACA_STARTING_CASH=100000.00
```

### 3. **Alpaca Service Created** ✅
A new service file created: `services/alpaca_service.py`

**This service includes 5 safety checks:**
1. ✅ Verifies URL contains "paper"
2. ✅ Verifies API key starts with "PK"
3. ✅ Verifies not in production environment
4. ✅ Verifies account number starts with "P"
5. ✅ Confirms account status

---

## 🔑 **NEXT STEP: Get Your API Keys**

### **Go to Alpaca and Sign Up:**

1. **Visit**: https://alpaca.markets/
2. **Click "Sign Up"** - It's 100% FREE
3. **Fill in your information**:
   - Name
   - Email  
   - Password
   - (No credit card required!)

### **Get Paper Trading Keys:**

1. After signing in, you'll see the dashboard
2. Look for **"Paper Trading"** section (usually top-right)
3. Click on **"View API Keys"** or **"Generate Keys"**
4. You'll see:
   - **API Key ID** - Starts with `PK` (Paper Key)
   - **Secret Key** - Long string of characters

### **IMPORTANT:**
- ✅ Use the **PAPER TRADING** keys (start with `PK`)
- ❌ Do **NOT** use live trading keys
- ✅ Paper trading is completely free and simulated

---

## 🔧 **Update Your Configuration**

Once you have your keys, update your `.env` file:

```bash
# Replace these lines in .env:
ALPACA_PAPER_API_KEY=YOUR_PAPER_API_KEY_HERE
ALPACA_PAPER_SECRET_KEY=YOUR_PAPER_SECRET_KEY_HERE

# With your actual keys:
ALPACA_PAPER_API_KEY=PKxxxxxxxxxxxxxxxxxx
ALPACA_PAPER_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 🧪 **Test Your Connection**

After updating `.env`, test the connection:

```bash
# Test script
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

# Check configuration
api_key = os.getenv('ALPACA_PAPER_API_KEY')
print(f'API Key configured: {api_key[:6]}...' if api_key else 'Not configured')
print(f'Starts with PK: {api_key.startswith(\"PK\")}' if api_key else 'N/A')
print(f'Base URL: {os.getenv(\"ALPACA_PAPER_BASE_URL\")}')
"
```

---

## ✅ **Verify It's Paper Trading**

Run this to confirm you're using paper trading:

```python
python << 'VERIFY'
import alpaca_trade_api as tradeapi
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('ALPACA_PAPER_API_KEY')
secret = os.getenv('ALPACA_PAPER_SECRET_KEY')
base_url = os.getenv('ALPACA_PAPER_BASE_URL')

alpaca = tradeapi.REST(api_key, secret, base_url)
account = alpaca.get_account()

print("="*60)
print("🧪 ALPACA PAPER TRADING VERIFICATION")
print("="*60)
print(f"Account Number: {account.account_number}")
print(f"Is Paper Account: {account.account_number.startswith('P')}")
print(f"Cash: ${float(account.cash):,.2f}")
print(f"Buying Power: ${float(account.buying_power):,.2f}")
print(f"Status: {account.status}")
print("="*60)
print("✅ THIS IS SIMULATED TRADING - NO REAL MONEY")
print("="*60)
VERIFY
```

Expected output:
```
============================================================
🧪 ALPACA PAPER TRADING VERIFICATION
============================================================
Account Number: PA1234567890
Is Paper Account: True
Cash: $100,000.00
Buying Power: $200,000.00
Status: ACTIVE
============================================================
✅ THIS IS SIMULATED TRADING - NO REAL MONEY
============================================================
```

---

## 🎯 **Next Steps After Setup**

Once your keys are configured:

1. **Restart your bot** - The AlpacaService will initialize automatically
2. **Check logs** - You should see "Alpaca Paper Trading ACTIVE"
3. **Test a trade** - Use `/trade AAPL` in Slack
4. **Verify in Alpaca dashboard** - Go to alpaca.markets and check Paper Trading section

---

## 🔒 **Safety Guarantees**

Your bot will **ONLY work with paper trading** because:

1. ✅ Code checks for "PK" prefix (paper keys)
2. ✅ Code checks for "paper" in URL
3. ✅ Code checks account starts with "P"
4. ✅ Separate API endpoints (paper vs live)
5. ✅ Environment must be "development"

**It's architecturally impossible to accidentally use live trading!**

---

## 📊 **What Happens When You Trade**

### With Alpaca Integrated:

1. User types `/trade AAPL` in Slack
2. Modal shows live price from Finnhub
3. User enters quantity and clicks Buy/Sell
4. Bot sends order to **Alpaca Paper Trading API**
5. Alpaca simulates execution against real market
6. Bot stores trade in **your DynamoDB**
7. User sees confirmation
8. Trade appears in **Alpaca dashboard** (paper section)

### Benefits:

- ✅ Real market prices
- ✅ Real order types (market, limit, stop-loss)
- ✅ Realistic execution (respects market hours)
- ✅ Professional trading experience
- ✅ Portfolio tracking
- ✅ Position management
- ✅ P&L calculations

---

## 🐛 **Troubleshooting**

### "Alpaca not available - using mock trading"

**Solution:** Check your `.env` file:
- Make sure keys are set (not placeholder text)
- Make sure `ALPACA_PAPER_ENABLED=true`
- Restart the bot

### "Authentication failed"

**Solution:**
- Verify your API keys are correct
- Make sure you copied the full keys (they're long!)
- Check you're using **paper trading keys** (start with PK)

### "Account not found"

**Solution:**
- Log into alpaca.markets
- Make sure you're in the **Paper Trading** section
- Click "View API Keys" to confirm they're correct

---

## 📚 **Additional Resources**

- **Alpaca Docs**: https://alpaca.markets/docs/
- **Paper Trading Dashboard**: https://app.alpaca.markets/paper/dashboard
- **API Reference**: https://alpaca.markets/docs/api-references/trading-api/

---

## 🎉 **You're Ready!**

Once you complete these steps, your trading bot will:
- ✅ Use real paper trading API
- ✅ Execute realistic simulated trades
- ✅ Track positions professionally
- ✅ Store everything in DynamoDB
- ✅ Provide production-quality experience

**All with $0 cost and 0 risk!** 🚀
