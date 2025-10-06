# How to Fix "dispatch_failed" Error for /risk-alert Commands

## ✅ Code Fix Complete!

The handlers are now properly registered in the code. All tests pass.

## ⚠️ What You Need to Do: Register Commands in Slack

The "dispatch_failed" error happens because **Slack doesn't know about the new commands yet**. You need to register them in your Slack App configuration.

---

## Step-by-Step Fix:

### 1. Go to Slack App Configuration

Visit: **https://api.slack.com/apps**

### 2. Select Your App

Click on: **"Jain Global Slack Trading Bot"**

### 3. Navigate to Slash Commands

- Look for **"Slash Commands"** in the left sidebar
- Click on it

### 4. Add the First Command

Click **"Create New Command"** button and fill in:

```
Command: /risk-alert
Request URL: https://slack.com/
Short Description: Create a risk alert for trade monitoring
Usage Hint: (leave empty)
Escape channels, users, and links sent to your app: ✓ (checked)
```

Click **"Save"**

### 5. Add the Second Command

Click **"Create New Command"** again and fill in:

```
Command: /risk-alerts
Request URL: https://slack.com/
Short Description: View and manage your risk alerts
Usage Hint: (leave empty)
Escape channels, users, and links sent to your app: ✓ (checked)
```

Click **"Save"**

### 6. Reinstall the App

**CRITICAL:** After adding commands, you MUST reinstall your app:

- Look for a yellow banner at the **TOP** of any page
- It will say **"Reinstall your app"** or similar
- Click the **"Reinstall App"** button
- Follow the prompts to authorize the app

### 7. Restart Your Python App

Stop and restart your app:

```bash
# Stop the current app (find the terminal and press Ctrl+C)
# Or kill it:
ps aux | grep "python.*app.py" | grep -v grep | awk '{print $2}' | xargs kill

# Start fresh:
python3 app.py
```

### 8. Test in Slack

Now try the commands in Slack:

```
/risk-alert
```

You should see a modal popup! 🎉

---

## Why Does This Happen?

Slack maintains its own registry of slash commands that are allowed for your app. Even though your Python code has the handlers, Slack won't forward commands to your app unless they're registered in the Slack App settings first.

Think of it like a whitelist: Slack only sends commands that it knows about.

---

## Troubleshooting

### Still getting "dispatch_failed"?

1. **Did you click "Reinstall App"?**
   - This is the most commonly forgotten step
   - Without it, Slack won't recognize the new commands

2. **Is your app running?**
   ```bash
   ps aux | grep "python.*app.py"
   ```

3. **Check the logs:**
   ```bash
   tail -f jain_global_slack_trading_bot.log | grep risk-alert
   ```

4. **Verify in Slack:**
   - Type just `/` in Slack
   - Do you see `/risk-alert` in the autocomplete list?
   - If NO → Commands not registered properly in Slack
   - If YES → Check if app is running

### Commands appear but modal doesn't open?

Check the app logs for errors:
```bash
tail -50 jain_global_slack_trading_bot.log
```

---

## Verification

After completing all steps, you should see:

✅ `/risk-alert` autocompletes when you type `/` in Slack  
✅ Running `/risk-alert` opens a modal for configuration  
✅ Logs show: "Risk alert handlers registered successfully"  
✅ No "dispatch_failed" errors

---

## Need Help?

If you're still having issues, share:
1. Screenshot of your Slash Commands page in Slack App settings
2. Output of `python3 test_config.py`
3. Last 20 lines of your app logs

