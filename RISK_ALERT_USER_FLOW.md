# Risk Alert Command - Complete User Flow

## 📋 **Overview**

The `/risk-alert` command allows users to create automated alerts for trades that meet specific risk criteria. This document outlines the complete user interaction flow and technical implementation.

---

## 🎯 **Step-by-Step User Experience**

### **Step 1: User Types Command**

**User Action:**
```
/risk-alert
```

**What Happens:**
- User types `/risk-alert` in any Slack channel
- Slack sends the command to the bot
- Bot receives the command request

**Technical Process:**
1. Slack sends POST request to bot with `trigger_id` (expires in 3 seconds!)
2. Bot handler `handle_risk_alert_command()` is triggered
3. Bot immediately calls `ack()` to acknowledge receipt
4. ⏱️ Timing logged: ACK response time

---

### **Step 2: Modal Opens**

**User Sees:**
A modal popup appears with the title **"Create Risk Alert"**

**Modal Contains:**

**Header:**
```
🚨 Configure Risk Alert Parameters
You'll be notified when trades match these criteria:
```

**Input Fields:**

1. **Alert Name** (Optional)
   - Placeholder: `e.g., High Risk Large Cap Alert`
   - Purpose: Give the alert a friendly name

2. **Minimum Trade Size ($)** (Required)
   - Placeholder: `e.g., 100000`
   - Hint: "Alert triggers when trade size exceeds this amount"
   - Example: Enter `100000` for $100,000

3. **Loss Threshold (%)** (Required)
   - Placeholder: `e.g., 5`
   - Hint: "Alert triggers when loss percentage exceeds this value"
   - Example: Enter `5` for 5% loss

4. **VIX Threshold** (Required)
   - Placeholder: `e.g., 20`
   - Hint: "Alert triggers when VIX level exceeds this value"
   - Example: Enter `20` for VIX above 20

5. **Notification Settings** (Checkboxes)
   - ☑️ **Scan existing trades now**
     - Description: "Check current open positions immediately"
   - ☑️ **Monitor new trades**
     - Description: "Alert on future trades that match criteria"

**Buttons:**
- **"Create Alert"** (Submit)
- **"Cancel"** (Close modal)

**Technical Process:**
1. Bot calls `create_risk_alert_modal()` to build modal JSON
2. Bot calls Slack API: `client.views_open(trigger_id, modal)`
3. ⏱️ Timing logged: Modal creation and API call time
4. Slack displays the modal to the user

---

### **Step 3: User Fills Out Form**

**User Actions:**

**Example Input:**
```
Alert Name: "Large Tech Stock Alert"
Minimum Trade Size: 50000
Loss Threshold: 3
VIX Threshold: 25
Notification Settings: ☑️ Both options checked
```

**What User Can Do:**
- Type values into text fields
- Check/uncheck notification options
- Click "Cancel" to abort
- Click "Create Alert" to submit

**Validation (Client-Side):**
- None (validation happens on submission)

---

### **Step 4: User Submits Form**

**User Action:**
Clicks **"Create Alert"** button

**What Happens:**
- Form data is sent to bot
- Bot validates the input
- If valid: Alert is created
- If invalid: Error messages shown

**Technical Process:**

1. **Handler Triggered:**
   - `handle_risk_alert_submission()` receives the form data
   - Callback ID: `"risk_alert_setup"`

2. **Data Extraction:**
   ```python
   alert_name = "Large Tech Stock Alert"
   trade_size = Decimal("50000")
   loss_percent = Decimal("3")
   vix_threshold = Decimal("25")
   notify_existing = True
   notify_new = True
   ```

3. **Validation:**
   - ✅ Trade size > 0
   - ✅ Loss percent between 0-100
   - ✅ VIX threshold between 0-100
   - ✅ At least one notification option selected

4. **If Validation Fails:**
   - Modal stays open
   - Error messages appear under invalid fields
   - Example: "Trade size must be positive"
   - User can fix and resubmit

5. **If Validation Passes:**
   - Modal closes
   - Alert creation process begins

---

### **Step 5: Alert Created & Saved**

**Technical Process:**

1. **Create Alert Object:**
   ```python
   alert_config = RiskAlertConfig(
       alert_id = "uuid-generated-automatically"
       manager_id = "U08GVNAPX3Q"  # User's Slack ID
       name = "Large Tech Stock Alert"
       trade_size_threshold = 50000
       loss_percent_threshold = 3
       vix_threshold = 25
       notify_on_existing = True
       notify_on_new = True
       status = AlertStatus.ACTIVE
       created_at = datetime.now()
   )
   ```

2. **Save to Database:**
   - `db_service.save_risk_alert(alert_config)`
   - Stored in DynamoDB table: `RiskAlertConfigs`
   - Indexed by: `alert_id` and `manager_id`

3. **Log Creation:**
   ```
   Risk alert abc123... created by U08GVNAPX3Q
   ```

**User Sees:**
Modal closes (no error = success)

---

### **Step 6: Confirmation Message Sent**

**User Sees:**
A message (DM or ephemeral) appears:

```
✅ Risk Alert Created Successfully!

Your alert 'Large Tech Stock Alert' has been set up with the following criteria:
• Min Trade Size: $50,000
• Min Loss %: 3%
• Min VIX: 25
• Monitor New Trades: Yes
• Scan Existing Trades: Yes

[Manage My Alerts] button
```

**Technical Process:**
1. `notification_service.send_alert_confirmation(user_id, alert_config)`
2. Creates formatted message blocks
3. Sends via Slack API: `client.chat_postMessage()` or `chat_postEphemeral()`

---

### **Step 7: Existing Trades Scanned (If Requested)**

**What Happens:**
If user checked "Scan existing trades now":

**Technical Process:**

1. **Get Current VIX:**
   - Fetch current VIX level from market data API
   - Example: VIX = 28.5

2. **Check VIX Against Threshold:**
   - If VIX (28.5) < threshold (25): ✅ Proceed
   - If VIX (15) < threshold (25): ❌ Skip (VIX too low)

3. **Query Database for Trades:**
   ```sql
   SELECT * FROM Trades 
   WHERE status = 'EXECUTED'
   AND (quantity * price) >= $50,000
   ```

4. **For Each Trade:**
   - Get current market price for the symbol
   - Calculate current loss percentage:
     ```
     If BUY trade:
       loss% = (trade_price - current_price) / trade_price * 100
     If SELL trade:
       loss% = (current_price - trade_price) / trade_price * 100
     ```
   
5. **Filter Matching Trades:**
   - Trade size >= $50,000 ✅
   - Loss% >= 3% ✅
   - VIX >= 25 ✅
   
   Example matching trade:
   ```
   AAPL: Bought at $175, now $169.75
   Trade size: $87,500
   Loss: 3% ($2,625)
   VIX: 28.5
   → MATCHES CRITERIA ✅
   ```

6. **Results:**
   - If matches found: Send summary notification
   - If no matches: Log "No existing trades match criteria"

**User Sees (If Matches Found):**

```
🔍 Risk Alert Scan: Large Tech Stock Alert

Alert Criteria:
• Trade Size: ≥ $50,000
• Loss Threshold: ≥ 3%
• VIX Level: ≥ 25

Found 3 Matching Trades:

• AAPL (BUY) - $87,500 @ $175.00 [View Trade]
• MSFT (BUY) - $125,000 @ $380.00 [View Trade]
• GOOGL (BUY) - $95,000 @ $142.00 [View Trade]

[Manage Alerts] button
```

**Technical Process:**
1. `alert_monitor.scan_existing_trades(alert_config)`
2. Returns list of matching Trade objects
3. `notification_service.send_risk_alert_summary(user_id, alert, trades)`
4. Creates formatted message with trade details
5. Sends to user

---

### **Step 8: Ongoing Monitoring (Future Trades)**

**What Happens:**
If user checked "Monitor new trades":

**Continuous Process:**

**When ANY trade is executed in the system:**

1. **Trade Executed:**
   ```
   User X executes: BUY TSLA 500 shares @ $250
   Trade size: $125,000
   ```

2. **Alert Monitor Triggered:**
   - `alert_monitor.check_trade_against_alerts(trade)`
   - Fetches all active alerts from database
   - Checks if this trade matches ANY alert criteria

3. **For This Alert:**
   ```
   Check if trade matches:
   - Trade size ($125,000) >= threshold ($50,000) ✅
   - Get current VIX: 28.5 >= threshold (25) ✅
   - Get current price: $245 (down from $250)
   - Calculate loss: 2% < threshold (3%) ❌
   
   Result: NO MATCH (loss not high enough yet)
   ```

4. **If Match Found:**
   - Create AlertTriggerEvent record
   - Send notification to alert creator
   - Update alert trigger count

**User Receives (When Match Found):**

```
🚨 Risk Alert: Large Tech Stock Alert

Trade: TSLA (BUY)
Trade ID: abc123...
Trade Size: $125,000
Loss %: 3.5%
VIX Level: 28.5
Alert Criteria Met: Yes

[View Alert Details] [View Trade]

Alert set by @you on Oct 6, 2025
```

**Technical Process:**
1. `alert_monitor._send_alert_notification(alert, trade, metrics)`
2. Creates trigger event:
   ```python
   trigger_event = AlertTriggerEvent(
       alert_id = "abc123..."
       manager_id = "U08GVNAPX3Q"
       trade_id = "trade-xyz"
       trade_size = 125000
       loss_percent = 3.5
       vix_level = 28.5
   )
   ```
3. `db_service.save_alert_trigger_event(trigger_event)`
4. `db_service.record_alert_trigger(alert_id)` - increments counter
5. `notification_service.send_single_trade_alert(manager_id, alert, trade, metrics)`

---

## 🔍 **Additional User Commands**

### **View All Alerts: `/risk-alerts`**

**User Action:**
```
/risk-alerts
```

**User Sees:**
```
📊 Your Risk Alerts

✅ Large Tech Stock Alert (abc123...)
  • Size: ≥ $50,000 | Loss: ≥ 3% | VIX: ≥ 25
  • Status: Active | Triggers: 12
  • Created: Oct 6, 2025
  [View/Edit]

⏸️ Small Cap Alert (def456...)
  • Size: ≥ $25,000 | Loss: ≥ 5% | VIX: ≥ 30
  • Status: Paused | Triggers: 3
  • Created: Oct 5, 2025
  [View/Edit]

[Create New Alert]
```

**Technical Process:**
1. `handle_list_alerts_command()` triggered
2. `db_service.get_manager_alerts(user_id, active_only=False)`
3. Fetches all alerts for this user
4. `create_alert_list_message(alerts)` formats the list
5. Sends ephemeral message

---

## 📊 **Complete Data Flow**

```
┌─────────────┐
│ User types  │
│ /risk-alert │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Slack sends     │
│ command payload │
└──────┬──────────┘
       │
       ▼
┌──────────────────────┐
│ Bot Handler          │
│ - ack()              │
│ - create_modal()     │
│ - views_open()       │
└──────┬───────────────┘
       │
       ▼
┌─────────────────┐
│ User fills form │
│ & submits       │
└──────┬──────────┘
       │
       ▼
┌───────────────────────┐
│ Submission Handler    │
│ - Validate inputs     │
│ - Create alert object │
│ - Save to database    │
└──────┬────────────────┘
       │
       ├──────────────────┐
       │                  │
       ▼                  ▼
┌──────────────┐   ┌─────────────────┐
│ Send         │   │ Scan existing   │
│ confirmation │   │ trades (if opt) │
└──────────────┘   └──────┬──────────┘
                          │
                          ▼
                   ┌─────────────────┐
                   │ Send summary    │
                   │ (if matches)    │
                   └─────────────────┘

       [ONGOING MONITORING]
              │
              ▼
┌──────────────────────────┐
│ New trade executed       │
│ anywhere in system       │
└──────┬───────────────────┘
       │
       ▼
┌────────────────────────────┐
│ Alert Monitor checks       │
│ trade against all alerts   │
└──────┬─────────────────────┘
       │
       ├─── Match? ──┐
       │             │
      YES           NO
       │             │
       ▼             ▼
┌─────────────┐  [Ignore]
│ Send alert  │
│ to manager  │
└─────────────┘
```

---

## 🗂️ **Database Records Created**

### **1. RiskAlertConfig Record:**
```json
{
  "alert_id": "550e8400-e29b-41d4-a716-446655440000",
  "manager_id": "U08GVNAPX3Q",
  "name": "Large Tech Stock Alert",
  "trade_size_threshold": "50000",
  "loss_percent_threshold": "3",
  "vix_threshold": "25",
  "status": "active",
  "created_at": "2025-10-06T21:00:00Z",
  "updated_at": "2025-10-06T21:00:00Z",
  "notify_on_existing": true,
  "notify_on_new": true,
  "notification_channel": "dm",
  "trigger_count": 0
}
```

### **2. AlertTriggerEvent Record (When Triggered):**
```json
{
  "event_id": "123e4567-e89b-12d3-a456-426614174000",
  "alert_id": "550e8400-e29b-41d4-a716-446655440000",
  "manager_id": "U08GVNAPX3Q",
  "trade_id": "trade-abc123",
  "triggered_at": "2025-10-06T21:30:00Z",
  "trade_size": "125000",
  "loss_percent": "3.5",
  "vix_level": "28.5",
  "context": {
    "trade_symbol": "TSLA",
    "trade_type": "BUY"
  }
}
```

---

## 🔐 **Current Permissions**

**Who Can Create Alerts:**
- ✅ **ALL USERS** (role restriction currently disabled)
- Note: Code has commented-out role restriction for Portfolio Managers/Admins

**What Users Can Access:**
- Own alerts only (isolated by `manager_id`)
- Cannot see or manage other users' alerts
- Each user's alert list is private

---

## 🚨 **Alert Criteria Logic**

**An alert triggers when ALL three conditions are met:**

```python
if (
    trade_size >= alert.trade_size_threshold AND
    loss_percent >= alert.loss_percent_threshold AND
    current_vix >= alert.vix_threshold
):
    → TRIGGER ALERT
```

**Example:**
```
Alert Settings:
- Min Trade Size: $50,000
- Min Loss: 3%
- Min VIX: 25

Trade Scenario:
- Trade Size: $125,000 ✅
- Loss: 3.5% ✅
- VIX: 28 ✅
→ ALL CONDITIONS MET → ALERT SENT

Trade Scenario 2:
- Trade Size: $125,000 ✅
- Loss: 2% ❌ (below 3%)
- VIX: 28 ✅
→ ONE CONDITION FAILED → NO ALERT
```

---

## 📝 **Summary**

**Total Steps in User Flow:**
1. Type `/risk-alert` command
2. Modal opens with form
3. Fill out parameters
4. Submit form
5. Validation occurs
6. Alert saved to database
7. Confirmation message received
8. Existing trades scanned (optional)
9. Summary sent if matches found (optional)
10. Ongoing monitoring for new trades (optional)

**Time Requirements:**
- Modal must open: < 3 seconds (Slack trigger_id timeout)
- Form submission: Immediate validation
- Existing scan: Variable (depends on trade count)
- Ongoing monitoring: Real-time (on each trade execution)

**User Benefits:**
- Set once, monitor continuously
- Automated notifications
- No manual checking required
- Customizable thresholds
- Immediate and ongoing alerts

