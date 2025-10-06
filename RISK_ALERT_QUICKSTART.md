# Risk Alert Feature - Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Run Integration Script (30 seconds)

```bash
cd "/Users/admin/Documents/Trade Simulator/TradeSimulationBot"
python3 scripts/integrate_risk_alerts.py
```

This automatically integrates the risk alert feature into your app.

### Step 2: Verify Configuration (1 minute)

```bash
# Run configuration test
python3 test_config.py

# Run risk alert tests
pytest tests/test_risk_alerts.py -v
```

### Step 3: Start Using! (2 minutes)

1. Start your Slack app:
   ```bash
   python3 app.py
   ```

2. In Slack, run:
   ```
   /risk-alert
   ```

3. Fill in the modal:
   - **Alert Name:** High Risk Alert
   - **Trade Size:** 100000
   - **Loss %:** 5
   - **VIX:** 20
   - ✅ Both notification options

4. Click "Create Alert"

**That's it!** You'll now receive notifications when trades match your criteria.

---

## 📖 What You Get

### For Portfolio Managers

**Create Alerts:**
- `/risk-alert` - Opens configuration modal
- Set thresholds for trade size, loss %, and VIX
- Scan existing trades immediately
- Monitor all future trades

**Manage Alerts:**
- `/risk-alerts` - View all your alerts
- Pause/resume alerts
- Edit criteria
- Delete alerts

**Receive Notifications:**
- Instant DM when trade matches
- Full trade details
- Quick action buttons
- Summary of existing matches

---

## 💡 Example Use Cases

### Use Case 1: High-Risk Large Position Alert
```
Alert Name: Large Position Alert
Trade Size: $500,000
Loss %: 5%
VIX: 25

Result: Get notified of any large position with 5%+ loss when VIX > 25
```

### Use Case 2: Volatile Market Alert
```
Alert Name: Volatility Spike Alert
Trade Size: $100,000
Loss %: 3%
VIX: 30

Result: Get notified during high volatility periods
```

### Use Case 3: Portfolio Risk Monitor
```
Alert Name: Portfolio Risk Monitor
Trade Size: $250,000
Loss %: 7%
VIX: 20

Result: Monitor significant losses in portfolio
```

---

## 🔍 Testing the Feature

### Quick Test (5 minutes)

1. **Create Test Alert:**
   ```
   /risk-alert
   Alert Name: Test Alert
   Trade Size: 1000
   Loss %: 0
   VIX: 0
   ✅ Scan existing trades
   ✅ Monitor new trades
   ```

2. **Execute Test Trade:**
   ```
   /trade
   Symbol: AAPL
   Quantity: 100
   Type: BUY
   ```

3. **Check for Notification:**
   - You should receive a DM with trade details
   - Notification includes all metrics
   - Action buttons available

4. **Manage Alert:**
   ```
   /risk-alerts
   ```
   - See your alert listed
   - Try pausing it
   - Try resuming it

5. **Clean Up:**
   - Delete test alert from the list

---

## 📊 What Gets Monitored

### Trade Metrics Checked:

1. **Trade Size**
   ```
   Trade Size = Quantity × Price
   Example: 1000 shares × $150 = $150,000
   ```

2. **Loss Percentage**
   ```
   For BUY: Loss % = (Entry Price - Current Price) / Entry Price × 100
   For SELL: Loss % = (Current Price - Entry Price) / Entry Price × 100
   ```

3. **VIX Level**
   ```
   Current VIX volatility index
   Fetched in real-time from market data
   Cached for 5 minutes
   ```

### Alert Triggers When:
```
trade_size >= threshold AND
loss_percent >= threshold AND
vix_level >= threshold
```

All three conditions must be met!

---

## 🎯 Common Scenarios

### Scenario 1: I want to monitor large trades only

```yaml
Trade Size: $1,000,000  # High threshold
Loss %: 0               # Any loss/gain
VIX: 0                  # Any volatility
```

### Scenario 2: I want alerts during high volatility

```yaml
Trade Size: $100,000    # Moderate threshold
Loss %: 3               # 3%+ loss
VIX: 30                 # High volatility
```

### Scenario 3: I want to monitor a specific risk level

```yaml
Trade Size: $250,000    # Specific threshold
Loss %: 5               # 5%+ loss
VIX: 20                 # Elevated volatility
```

### Scenario 4: I want comprehensive monitoring

```yaml
Trade Size: $50,000     # Low threshold (catches most)
Loss %: 2               # 2%+ loss
VIX: 15                 # Moderate volatility
```

---

## 🔧 Troubleshooting

### Alert not triggering?

**Check 1:** Is alert ACTIVE?
```
/risk-alerts
Look for ✅ (active) not ⏸️ (paused)
```

**Check 2:** Are ALL three criteria met?
- Trade size must be ≥ threshold
- Loss % must be ≥ threshold  
- VIX must be ≥ threshold

**Check 3:** Is "Monitor new trades" enabled?
- Must be checked when creating alert
- Check alert settings in `/risk-alerts`

### Not receiving notifications?

**Check 1:** Verify Slack DM settings
- Ensure DMs are enabled
- Check notification preferences

**Check 2:** Check app logs
```bash
tail -f jain_global_slack_trading_bot.log | grep "alert"
```

**Check 3:** Test with low thresholds
- Create alert with all thresholds at 0
- Execute any trade
- Should get notification immediately

### Integration failing?

**Option 1:** Run integration script again
```bash
python3 scripts/integrate_risk_alerts.py
```

**Option 2:** Manual integration
- Follow `RISK_ALERT_INTEGRATION.md`
- Check each step carefully

**Option 3:** Check logs
```bash
# Look for integration errors
grep -i "risk.*alert" jain_global_slack_trading_bot.log
```

---

## 📚 More Information

- **Full Documentation:** `RISK_ALERT_INTEGRATION.md`
- **Implementation Details:** `RISK_ALERT_IMPLEMENTATION_SUMMARY.md`
- **Test Suite:** `tests/test_risk_alerts.py`
- **Source Code:** 
  - Models: `models/risk_alert.py`
  - Service: `services/alert_monitor.py`
  - UI: `ui/risk_alert_widget.py`
  - Handlers: `listeners/risk_alert_handlers.py`

---

## 🎓 Pro Tips

1. **Start Conservative**
   - Begin with high thresholds
   - Reduce gradually based on results
   - Avoid alert fatigue

2. **Use Descriptive Names**
   - "High Vol Large Cap Alert"
   - "Portfolio Risk Monitor"
   - "Earnings Season Alert"

3. **Multiple Alerts**
   - Create different alerts for different scenarios
   - One for each risk level
   - Pause/resume as needed

4. **Regular Review**
   - Check `/risk-alerts` weekly
   - Review trigger counts
   - Adjust thresholds

5. **Leverage Existing Scan**
   - Always check "Scan existing trades"
   - Immediate visibility into current risk
   - Catch issues right away

---

## ✅ Success!

You're now ready to use the Risk Alert feature!

**Next Steps:**
1. ✅ Create your first alert
2. ✅ Monitor notifications
3. ✅ Adjust thresholds as needed
4. ✅ Create additional alerts for different scenarios

**Need Help?**
- 📖 Read full documentation
- 🧪 Run test suite
- 📝 Check logs
- 💬 Contact support team

---

**Happy Monitoring! 🚀**


