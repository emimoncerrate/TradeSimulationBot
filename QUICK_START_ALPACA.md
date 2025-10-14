# 🚀 Quick Start: Alpaca Integration

## Get Trading in 5 Minutes

### 1️⃣ Get API Keys (2 minutes)
```bash
1. Go to https://alpaca.markets
2. Sign up for free
3. Navigate to "Paper Trading" → "API Keys"
4. Click "Generate New Key"
5. Copy Key ID and Secret Key
```

### 2️⃣ Configure (1 minute)
Add to your `.env` file:
```bash
# Enable Alpaca
ALPACA_ENABLED=true
ALPACA_API_KEY=your-key-id-here
ALPACA_SECRET_KEY=your-secret-key-here
ALPACA_PAPER_TRADING=true

# Enable real trading
USE_REAL_TRADING=true
```

### 3️⃣ Install (30 seconds)
```bash
pip install -r requirements.txt
```

### 4️⃣ Test (1 minute)
```bash
python test_alpaca_integration.py
```

### 5️⃣ Trade! (30 seconds)
```bash
# Start your app
python app.py

# In Slack, use:
/trade AAPL
```

## ✅ That's It!

Your Slack bot now executes real trades via Alpaca!

---

## 📋 What You Get

✅ **Real Market Orders** - Trades execute on live markets  
✅ **Paper Trading** - Safe testing with $100k virtual money  
✅ **Commission-Free** - No trading fees  
✅ **Real-Time Fills** - Actual market execution  
✅ **Position Tracking** - See your portfolio  
✅ **Professional Platform** - Used by traders worldwide  

---

## 🔄 Trade Flow

```
Slack /trade → Your Bot → Alpaca API → Market → Execution → Slack
```

That's it! Real trading from Slack in under 5 minutes.

---

## 📚 Full Documentation

- **Setup Guide**: `ALPACA_SETUP_GUIDE.md`
- **Implementation Details**: `ALPACA_INTEGRATION_SUMMARY.md`
- **Test Script**: `python test_alpaca_integration.py`

---

## 🆘 Need Help?

**Test not passing?**
```bash
python test_alpaca_integration.py
```
The test will tell you exactly what's wrong.

**Want more details?**
Read `ALPACA_SETUP_GUIDE.md`

**Ready for live trading?**
Change in `.env`:
```bash
ALPACA_PAPER_TRADING=false
ALPACA_BASE_URL=https://api.alpaca.markets
```
⚠️ **But start with paper trading first!**

---

## 🎯 Pro Tips

1. **Always test first** - Run the test script
2. **Start with paper** - Use ALPACA_PAPER_TRADING=true
3. **Test in Slack** - Execute a few trades to verify
4. **Monitor closely** - Watch your first few real trades
5. **Start small** - Trade 1 share until comfortable

---

**You're ready to trade! 🎉**

