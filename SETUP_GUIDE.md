# 🚀 TradeSimulator Setup Guide

## Step 1: Configure Your Slack App

### A. Get Your Slack Tokens

1. **Go to your Slack App**: https://api.slack.com/apps
   - If you don't have an app yet, click "Create New App" → "From scratch"
   - Name it "TradeSimulator" and select your workspace

2. **Get Bot Token** (SLACK_BOT_TOKEN):
   - Go to "OAuth & Permissions" in the left sidebar
   - Scroll down to "Scopes" → "Bot Token Scopes"
   - Add these scopes if not already added:
     - `app_mentions:read`
     - `channels:history`
     - `channels:read`
     - `chat:write`
     - `commands`
     - `im:history`
     - `im:read`
     - `im:write`
     - `users:read`
     - `users:read.email`
   - Scroll up and click "Install to Workspace" (or "Reinstall App")
   - Copy the "Bot User OAuth Token" (starts with `xoxb-`)

3. **Get Signing Secret** (SLACK_SIGNING_SECRET):
   - Go to "Basic Information" in the left sidebar
   - Scroll down to "App Credentials"
   - Copy the "Signing Secret"

4. **Get App-Level Token** (SLACK_APP_TOKEN) - For Socket Mode:
   - Go to "Basic Information"
   - Scroll down to "App-Level Tokens"
   - Click "Generate Token and Scopes"
   - Name it "socket_token"
   - Add scope: `connections:write`
   - Click "Generate"
   - Copy the token (starts with `xapp-`)

5. **Enable Socket Mode**:
   - Go to "Socket Mode" in the left sidebar
   - Toggle "Enable Socket Mode" to ON

6. **Add Slash Commands**:
   - Go to "Slash Commands" in the left sidebar
   - Create these commands:
     - `/trade` - "Execute a trade"
     - `/portfolio` - "View your portfolio"
     - `/market` - "Get market prices"
   - For each command, you can use a placeholder URL like: `https://example.com/slack/commands`
   - (Socket Mode doesn't require actual URLs, but Slack requires something)

7. **Enable Interactivity**:
   - Go to "Interactivity & Shortcuts"
   - Toggle "Interactivity" to ON
   - Use placeholder URL: `https://example.com/slack/interactions`

8. **Get Channel ID**:
   - In Slack, right-click on the channel you want to use
   - Click "View channel details"
   - Scroll down and copy the Channel ID (e.g., `C1234567890`)

## Step 2: Get Finnhub API Key (Free)

1. Go to: https://finnhub.io/register
2. Sign up for a free account
3. After login, your API key will be on the dashboard
4. Copy the API key

## Step 3: Update Your .env File

Run this command and paste your tokens:
```bash
nano .env
```

Update these lines:
```env
SLACK_BOT_TOKEN=xoxb-paste-your-token-here
SLACK_SIGNING_SECRET=paste-your-secret-here
SLACK_APP_TOKEN=xapp-paste-your-token-here
FINNHUB_API_KEY=paste-your-api-key-here
APPROVED_CHANNELS=paste-your-channel-id-here
```

Save and exit (Ctrl+O, Enter, Ctrl+X)

## Step 4: Install Dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Step 5: Run the Bot!

### Option A: Run Locally (Simple)
```bash
python app.py
```

### Option B: Run with Docker
```bash
docker-compose up --build
```

## Step 6: Test in Slack

Go to your Slack channel and try:
```
/trade buy AAPL 10
/portfolio
/market TSLA
```

## 🎉 You're All Set!

The bot should respond to your commands. If you encounter any issues, check the logs for error messages.

---

## Quick Troubleshooting

**Bot doesn't respond:**
- Check that Socket Mode is enabled
- Verify all tokens are correct in .env
- Make sure the bot is invited to your channel
- Check the terminal for error messages

**Market data errors:**
- Verify your Finnhub API key is correct
- Check if you've exceeded the free tier limit (60 calls/min)

**Permission errors:**
- Make sure you added all required OAuth scopes
- Reinstall the app after adding scopes
