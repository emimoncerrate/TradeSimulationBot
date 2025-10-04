#!/bin/bash

# =============================================================================
# Jain Global Slack Trading Bot - Slack App Configuration Script
# =============================================================================
# This script helps configure the Slack application with proper permissions,
# endpoints, and settings for the trading bot.
#
# Usage:
#   ./scripts/configure-slack-app.sh [environment] [api-gateway-url]
#
# Examples:
#   ./scripts/configure-slack-app.sh development https://abc123.execute-api.us-east-1.amazonaws.com/development
#   ./scripts/configure-slack-app.sh production https://xyz789.execute-api.us-east-1.amazonaws.com/production
# =============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# =============================================================================
# CONFIGURATION
# =============================================================================

ENVIRONMENT=${1:-development}
API_GATEWAY_URL=${2:-""}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# VALIDATION
# =============================================================================

if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    log_error "Valid environments: development, staging, production"
    exit 1
fi

if [[ -z "$API_GATEWAY_URL" ]]; then
    log_error "API Gateway URL is required"
    log_error "Usage: $0 [environment] [api-gateway-url]"
    exit 1
fi

# Validate URL format
if [[ ! "$API_GATEWAY_URL" =~ ^https://.*\.execute-api\..*\.amazonaws\.com/.* ]]; then
    log_error "Invalid API Gateway URL format"
    log_error "Expected format: https://api-id.execute-api.region.amazonaws.com/stage"
    exit 1
fi

# =============================================================================
# SLACK APP CONFIGURATION GENERATION
# =============================================================================

log_info "Generating Slack app configuration for $ENVIRONMENT environment..."

# Create configuration directory
mkdir -p config/slack

# Generate app manifest
cat > "config/slack/app-manifest-${ENVIRONMENT}.json" << EOF
{
  "display_information": {
    "name": "Jain Trading Bot (${ENVIRONMENT})",
    "description": "Professional trading simulation bot for Jain Global investment team",
    "background_color": "#1f2937",
    "long_description": "The Jain Trading Bot enables traders, analysts, and portfolio managers to simulate trades directly within Slack. Features include AI-powered risk analysis, real-time market data integration, and comprehensive portfolio tracking."
  },
  "features": {
    "app_home": {
      "home_tab_enabled": true,
      "messages_tab_enabled": true,
      "messages_tab_read_only_enabled": false
    },
    "bot_user": {
      "display_name": "Jain Trading Bot",
      "always_online": true
    },
    "shortcuts": [],
    "slash_commands": [
      {
        "command": "/trade",
        "url": "${API_GATEWAY_URL}/slack/commands",
        "description": "Initiate a trade simulation",
        "usage_hint": "Enter trade details in the modal",
        "should_escape": false
      }
    ]
  },
  "oauth_config": {
    "scopes": {
      "bot": [
        "app_mentions:read",
        "channels:history",
        "channels:read",
        "chat:write",
        "commands",
        "groups:history",
        "groups:read",
        "im:history",
        "im:read",
        "im:write",
        "mpim:history",
        "mpim:read",
        "mpim:write",
        "users:read",
        "users:read.email"
      ]
    }
  },
  "settings": {
    "event_subscriptions": {
      "request_url": "${API_GATEWAY_URL}/slack/events",
      "bot_events": [
        "app_home_opened",
        "app_mention",
        "message.channels",
        "message.groups",
        "message.im",
        "message.mpim"
      ]
    },
    "interactivity": {
      "is_enabled": true,
      "request_url": "${API_GATEWAY_URL}/slack/interactive"
    },
    "org_deploy_enabled": false,
    "socket_mode_enabled": false,
    "token_rotation_enabled": false
  }
}
EOF

log_success "App manifest generated: config/slack/app-manifest-${ENVIRONMENT}.json"

# =============================================================================
# SLACK APP SETUP INSTRUCTIONS
# =============================================================================

cat > "config/slack/setup-instructions-${ENVIRONMENT}.md" << EOF
# Slack App Setup Instructions - ${ENVIRONMENT}

## Overview
This document provides step-by-step instructions for configuring the Jain Trading Bot Slack application for the **${ENVIRONMENT}** environment.

## Prerequisites
- Admin access to the Slack workspace
- API Gateway URL: \`${API_GATEWAY_URL}\`

## Step 1: Create Slack App

### Option A: Using App Manifest (Recommended)
1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click **"Create New App"**
3. Select **"From an app manifest"**
4. Choose your workspace
5. Copy and paste the contents of \`config/slack/app-manifest-${ENVIRONMENT}.json\`
6. Review the configuration and click **"Create"**

### Option B: Manual Configuration
1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From scratch"**
3. App Name: \`Jain Trading Bot (${ENVIRONMENT})\`
4. Workspace: Select your workspace
5. Click **"Create App"**

## Step 2: Configure OAuth & Permissions

1. Navigate to **"OAuth & Permissions"** in the left sidebar
2. Scroll down to **"Scopes"**
3. Add the following **Bot Token Scopes**:
   - \`app_mentions:read\` - View messages that directly mention your bot
   - \`channels:history\` - View messages and other content in public channels
   - \`channels:read\` - View basic information about public channels
   - \`chat:write\` - Send messages as the bot
   - \`commands\` - Add shortcuts and/or slash commands
   - \`groups:history\` - View messages and other content in private channels
   - \`groups:read\` - View basic information about private channels
   - \`im:history\` - View messages and other content in direct messages
   - \`im:read\` - View basic information about direct messages
   - \`im:write\` - Start direct messages with people
   - \`mpim:history\` - View messages and other content in group direct messages
   - \`mpim:read\` - View basic information about group direct messages
   - \`mpim:write\` - Start group direct messages with people
   - \`users:read\` - View people in the workspace
   - \`users:read.email\` - View email addresses of people in the workspace

4. Click **"Install to Workspace"**
5. Authorize the app
6. Copy the **Bot User OAuth Token** (starts with \`xoxb-\`)

## Step 3: Configure App Home

1. Navigate to **"App Home"** in the left sidebar
2. Enable **"Home Tab"**
3. Enable **"Messages Tab"**
4. Disable **"Allow users to send Slash commands and messages from the messages tab"**

## Step 4: Configure Interactivity & Shortcuts

1. Navigate to **"Interactivity & Shortcuts"** in the left sidebar
2. Turn on **"Interactivity"**
3. Set **Request URL** to: \`${API_GATEWAY_URL}/slack/interactive\`
4. Click **"Save Changes"**

## Step 5: Configure Slash Commands

1. Navigate to **"Slash Commands"** in the left sidebar
2. Click **"Create New Command"**
3. Configure the command:
   - **Command**: \`/trade\`
   - **Request URL**: \`${API_GATEWAY_URL}/slack/commands\`
   - **Short Description**: \`Initiate a trade simulation\`
   - **Usage Hint**: \`Enter trade details in the modal\`
4. Click **"Save"**

## Step 6: Configure Event Subscriptions

1. Navigate to **"Event Subscriptions"** in the left sidebar
2. Turn on **"Enable Events"**
3. Set **Request URL** to: \`${API_GATEWAY_URL}/slack/events\`
4. Wait for URL verification (should show ✅ Verified)
5. Expand **"Subscribe to bot events"**
6. Add the following events:
   - \`app_home_opened\` - User clicked into your App Home
   - \`app_mention\` - Subscribe to only the message events that mention your app
   - \`message.channels\` - A message was posted to a channel
   - \`message.groups\` - A message was posted to a private channel
   - \`message.im\` - A message was posted in a direct message channel
   - \`message.mpim\` - A message was posted in a multiparty direct message channel
7. Click **"Save Changes"**

## Step 7: Get App Credentials

1. Navigate to **"Basic Information"** in the left sidebar
2. Scroll down to **"App Credentials"**
3. Copy the following values:
   - **Signing Secret** (click "Show" to reveal)
   - **App ID**
   - **Client ID**
   - **Client Secret** (if needed for OAuth flow)

## Step 8: Configure Environment Variables

Update your \`.env\` file with the following values:

\`\`\`bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_APP_ID=your-app-id-here
\`\`\`

## Step 9: Test the Configuration

1. **Health Check**:
   \`\`\`bash
   curl ${API_GATEWAY_URL}/health
   \`\`\`

2. **Slack Integration Test**:
   - Go to your Slack workspace
   - Add the bot to a private channel: \`/invite @jain-trading-bot\`
   - Type \`/trade\` in the channel
   - Verify the modal opens correctly

3. **App Home Test**:
   - Click on the bot name in the sidebar
   - Verify the App Home tab loads with portfolio dashboard

## Step 10: Channel Configuration

### Add Approved Channels
The bot only works in pre-approved private channels. To add channels:

1. **Get Channel ID**:
   - Right-click on the channel name
   - Select "Copy link"
   - Extract the channel ID from the URL (e.g., \`C1234567890\`)

2. **Update Environment Variables**:
   \`\`\`bash
   APPROVED_CHANNELS=C1234567890,C0987654321,C1122334455
   \`\`\`

3. **Redeploy the Application**:
   \`\`\`bash
   ./scripts/deploy-infrastructure.sh ${ENVIRONMENT} us-east-1
   \`\`\`

### Channel Setup Process
1. Create a private channel for trading (e.g., \`#trading-${ENVIRONMENT}\`)
2. Add relevant team members (traders, analysts, portfolio managers)
3. Invite the bot: \`/invite @jain-trading-bot\`
4. Add the channel ID to \`APPROVED_CHANNELS\`
5. Test the \`/trade\` command

## Troubleshooting

### Common Issues

1. **URL Verification Failed**:
   - Ensure the Lambda function is deployed and running
   - Check CloudWatch logs for errors
   - Verify the API Gateway URL is correct

2. **Slash Command Not Working**:
   - Verify the command URL is set correctly
   - Check that the bot is invited to the channel
   - Ensure the channel is in the approved channels list

3. **Modal Not Opening**:
   - Check Lambda function logs
   - Verify interactivity URL is configured
   - Ensure proper OAuth scopes are granted

4. **App Home Not Loading**:
   - Verify App Home is enabled
   - Check for JavaScript errors in browser console
   - Review Lambda logs for App Home events

### Log Analysis
\`\`\`bash
# Check Lambda logs
aws logs tail /aws/lambda/jain-trading-bot-${ENVIRONMENT}-lambda --follow

# Check API Gateway logs
aws logs tail /aws/apigateway/jain-trading-bot-${ENVIRONMENT}-api --follow
\`\`\`

## Security Considerations

1. **Token Security**:
   - Never commit tokens to version control
   - Use AWS Systems Manager Parameter Store for production
   - Rotate tokens regularly

2. **Channel Restrictions**:
   - Only approved private channels can use the bot
   - Regular audit of approved channels list
   - Monitor for unauthorized access attempts

3. **User Permissions**:
   - Role-based access control within the bot
   - Regular review of user roles and permissions
   - Audit trail for all trading activities

## Support

For issues with Slack app configuration:
- **Development**: dev-team@jainglobal.com
- **Infrastructure**: infra-team@jainglobal.com
- **Slack Admin**: slack-admin@jainglobal.com

## Next Steps

After completing the Slack app setup:
1. Test all functionality in the ${ENVIRONMENT} environment
2. Configure monitoring and alerting
3. Train users on the bot functionality
4. Set up regular maintenance procedures

---

**Environment**: ${ENVIRONMENT}  
**API Gateway URL**: ${API_GATEWAY_URL}  
**Generated**: $(date)
EOF

log_success "Setup instructions generated: config/slack/setup-instructions-${ENVIRONMENT}.md"

# =============================================================================
# SLACK APP VALIDATION SCRIPT
# =============================================================================

cat > "scripts/validate-slack-config.sh" << 'EOF'
#!/bin/bash

# =============================================================================
# Slack Configuration Validation Script
# =============================================================================

set -e

ENVIRONMENT=${1:-development}
API_GATEWAY_URL=${2:-""}

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }

# Validation counters
PASSED=0
FAILED=0
WARNINGS=0

validate_environment_vars() {
    log_info "Validating Slack environment variables..."
    
    if [[ -z "${SLACK_BOT_TOKEN:-}" ]]; then
        log_error "SLACK_BOT_TOKEN is not set"
        ((FAILED++))
    elif [[ "${SLACK_BOT_TOKEN}" == xoxb-* ]]; then
        log_success "SLACK_BOT_TOKEN is properly formatted"
        ((PASSED++))
    else
        log_error "SLACK_BOT_TOKEN has invalid format (should start with xoxb-)"
        ((FAILED++))
    fi
    
    if [[ -z "${SLACK_SIGNING_SECRET:-}" ]]; then
        log_error "SLACK_SIGNING_SECRET is not set"
        ((FAILED++))
    elif [[ ${#SLACK_SIGNING_SECRET} -eq 32 ]]; then
        log_success "SLACK_SIGNING_SECRET is properly formatted"
        ((PASSED++))
    else
        log_warning "SLACK_SIGNING_SECRET length is unusual (expected 32 characters)"
        ((WARNINGS++))
    fi
}

validate_api_endpoints() {
    log_info "Validating API endpoints..."
    
    if [[ -z "$API_GATEWAY_URL" ]]; then
        log_error "API Gateway URL not provided"
        ((FAILED++))
        return
    fi
    
    ENDPOINTS=("health" "slack/events" "slack/interactive" "slack/commands")
    
    for endpoint in "${ENDPOINTS[@]}"; do
        URL="${API_GATEWAY_URL}/${endpoint}"
        
        if [[ "$endpoint" == "health" ]]; then
            # Health endpoint should return 200
            if curl -s -f "$URL" > /dev/null; then
                log_success "Health endpoint is responding: $URL"
                ((PASSED++))
            else
                log_error "Health endpoint is not responding: $URL"
                ((FAILED++))
            fi
        else
            # Slack endpoints should return 400 for GET requests (expecting POST)
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || echo "000")
            if [[ "$HTTP_CODE" == "400" || "$HTTP_CODE" == "405" ]]; then
                log_success "Slack endpoint is configured: $URL"
                ((PASSED++))
            else
                log_error "Slack endpoint is not responding correctly: $URL (HTTP $HTTP_CODE)"
                ((FAILED++))
            fi
        fi
    done
}

validate_slack_app_config() {
    log_info "Validating Slack app configuration files..."
    
    MANIFEST_FILE="config/slack/app-manifest-${ENVIRONMENT}.json"
    INSTRUCTIONS_FILE="config/slack/setup-instructions-${ENVIRONMENT}.md"
    
    if [[ -f "$MANIFEST_FILE" ]]; then
        log_success "App manifest exists: $MANIFEST_FILE"
        ((PASSED++))
        
        # Validate JSON syntax
        if jq empty "$MANIFEST_FILE" 2>/dev/null; then
            log_success "App manifest has valid JSON syntax"
            ((PASSED++))
        else
            log_error "App manifest has invalid JSON syntax"
            ((FAILED++))
        fi
    else
        log_error "App manifest not found: $MANIFEST_FILE"
        ((FAILED++))
    fi
    
    if [[ -f "$INSTRUCTIONS_FILE" ]]; then
        log_success "Setup instructions exist: $INSTRUCTIONS_FILE"
        ((PASSED++))
    else
        log_error "Setup instructions not found: $INSTRUCTIONS_FILE"
        ((FAILED++))
    fi
}

test_slack_integration() {
    log_info "Testing Slack integration (if configured)..."
    
    if [[ -n "${SLACK_BOT_TOKEN:-}" && -n "$API_GATEWAY_URL" ]]; then
        # Test Slack API connectivity
        if curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
               "https://slack.com/api/auth.test" | jq -r '.ok' | grep -q "true"; then
            log_success "Slack API authentication successful"
            ((PASSED++))
        else
            log_error "Slack API authentication failed"
            ((FAILED++))
        fi
    else
        log_warning "Skipping Slack integration test (missing credentials)"
        ((WARNINGS++))
    fi
}

# Run all validations
log_info "Starting Slack configuration validation for $ENVIRONMENT environment"
echo

validate_environment_vars
validate_api_endpoints
validate_slack_app_config
test_slack_integration

# Summary
echo
log_info "=== VALIDATION SUMMARY ==="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo

if [[ $FAILED -eq 0 ]]; then
    log_success "Slack configuration validation completed successfully!"
    exit 0
else
    log_error "Slack configuration validation failed with $FAILED errors"
    exit 1
fi
EOF

chmod +x scripts/validate-slack-config.sh
log_success "Slack validation script created: scripts/validate-slack-config.sh"

# =============================================================================
# WORKSPACE INSTALLATION GUIDE
# =============================================================================

cat > "config/slack/workspace-installation-guide.md" << EOF
# Slack Workspace Installation Guide

## Overview
This guide provides instructions for installing and distributing the Jain Trading Bot across different Slack workspaces and environments.

## Installation Types

### 1. Development Installation
- **Purpose**: Testing and development
- **Workspace**: Development/staging workspace
- **Distribution**: Manual installation by developers

### 2. Production Installation
- **Purpose**: Live trading operations
- **Workspace**: Production workspace
- **Distribution**: Controlled deployment by administrators

## Pre-Installation Checklist

### Technical Requirements
- [ ] AWS infrastructure deployed and validated
- [ ] API Gateway endpoints accessible
- [ ] Environment variables configured
- [ ] Monitoring and logging enabled

### Slack Workspace Requirements
- [ ] Workspace admin access
- [ ] Private channels created for trading
- [ ] Team members identified and roles assigned
- [ ] Security policies reviewed and approved

### Security Requirements
- [ ] Bot token secured (not in version control)
- [ ] Signing secret configured
- [ ] Channel restrictions implemented
- [ ] User access controls defined

## Installation Process

### Step 1: Prepare Slack App
1. Use the app manifest from \`config/slack/app-manifest-${ENVIRONMENT}.json\`
2. Follow setup instructions in \`config/slack/setup-instructions-${ENVIRONMENT}.md\`
3. Configure all required OAuth scopes and permissions

### Step 2: Configure Endpoints
Set the following URLs in your Slack app configuration:
- **Events**: \`${API_GATEWAY_URL}/slack/events\`
- **Interactivity**: \`${API_GATEWAY_URL}/slack/interactive\`
- **Slash Commands**: \`${API_GATEWAY_URL}/slack/commands\`

### Step 3: Install to Workspace
1. Click "Install to Workspace" in the Slack app settings
2. Authorize the requested permissions
3. Copy the Bot User OAuth Token
4. Update environment variables with the token

### Step 4: Configure Channels
1. Create private channels for trading activities
2. Add relevant team members to channels
3. Invite the bot to approved channels: \`/invite @jain-trading-bot\`
4. Update \`APPROVED_CHANNELS\` environment variable
5. Redeploy the application with updated channel list

### Step 5: Test Installation
1. Run validation script: \`./scripts/validate-slack-config.sh ${ENVIRONMENT} ${API_GATEWAY_URL}\`
2. Test slash command: \`/trade\` in approved channel
3. Verify App Home functionality
4. Test user roles and permissions

## User Onboarding

### Role Assignment
Configure users with appropriate roles:

#### Research Analyst
- **Permissions**: Create trade proposals, view analysis
- **Features**: Enhanced idea testing, proposal generation
- **Channels**: Research and analysis channels

#### Portfolio Manager
- **Permissions**: Approve trades, view all portfolios, risk analysis
- **Features**: Comprehensive risk analysis, decision tools
- **Channels**: All trading channels, management channels

#### Execution Trader
- **Permissions**: Execute approved trades, view execution status
- **Features**: Clear trade instructions, execution confirmation
- **Channels**: Execution channels, specific trading desks

### Training Materials
Provide users with:
1. Bot functionality overview
2. Command reference guide
3. Risk analysis interpretation
4. Troubleshooting common issues

## Multi-Workspace Deployment

### Workspace Strategy
- **Development**: \`dev-workspace.slack.com\`
- **Staging**: \`staging-workspace.slack.com\`
- **Production**: \`jainglobal.slack.com\`

### Configuration Management
Each workspace requires:
- Separate Slack app registration
- Environment-specific API endpoints
- Workspace-specific channel configurations
- Role mappings for workspace users

### Deployment Coordination
1. Deploy infrastructure first
2. Configure Slack app for each workspace
3. Test in development workspace
4. Promote to staging workspace
5. Deploy to production workspace

## Security and Compliance

### Access Control
- Bot only functions in approved private channels
- Role-based feature access within bot
- Regular audit of user permissions and channel access

### Data Protection
- All communications encrypted in transit
- Audit logging for all trading activities
- No sensitive data stored in Slack messages

### Compliance Monitoring
- Trade execution audit trails
- User activity logging
- Regular security reviews

## Maintenance and Updates

### Regular Maintenance
- **Weekly**: Review bot usage and error logs
- **Monthly**: Update approved channels list
- **Quarterly**: Review user roles and permissions

### App Updates
1. Test updates in development workspace
2. Deploy to staging workspace for validation
3. Schedule production deployment during maintenance window
4. Notify users of new features or changes

### Token Rotation
- Rotate bot tokens quarterly
- Update environment variables
- Redeploy application
- Verify functionality after rotation

## Troubleshooting

### Common Installation Issues

#### Bot Not Responding
- Verify bot is invited to channel
- Check channel is in approved list
- Review Lambda function logs

#### Permission Errors
- Verify OAuth scopes are granted
- Check bot token validity
- Review IAM permissions

#### Endpoint Verification Failed
- Confirm API Gateway is deployed
- Check Lambda function is running
- Verify URL configuration in Slack app

### Support Escalation
- **Level 1**: Check documentation and logs
- **Level 2**: Contact development team
- **Level 3**: Escalate to infrastructure team

## Monitoring and Analytics

### Usage Metrics
Track the following metrics:
- Number of active users
- Trade simulation volume
- Channel activity levels
- Error rates and types

### Performance Monitoring
- Response time for slash commands
- Modal loading performance
- API endpoint availability
- Database query performance

### Business Metrics
- User adoption rates
- Feature utilization
- Trading decision impact
- Risk analysis effectiveness

## Rollback Procedures

### Emergency Rollback
If critical issues occur:
1. Disable Slack app (remove from workspace)
2. Rollback AWS infrastructure to previous version
3. Notify users of temporary unavailability
4. Investigate and fix issues
5. Redeploy and re-enable

### Planned Rollback
For planned rollbacks:
1. Schedule maintenance window
2. Notify users in advance
3. Rollback infrastructure
4. Update Slack app configuration
5. Test functionality
6. Notify users of completion

---

**Environment**: ${ENVIRONMENT}  
**API Gateway URL**: ${API_GATEWAY_URL}  
**Generated**: $(date)
EOF

log_success "Workspace installation guide created: config/slack/workspace-installation-guide.md"

# =============================================================================
# SUMMARY AND NEXT STEPS
# =============================================================================

echo
log_success "=== SLACK APP CONFIGURATION COMPLETED ==="
echo
log_info "Generated Files:"
log_info "  - config/slack/app-manifest-${ENVIRONMENT}.json"
log_info "  - config/slack/setup-instructions-${ENVIRONMENT}.md"
log_info "  - config/slack/workspace-installation-guide.md"
log_info "  - scripts/validate-slack-config.sh"
echo
log_info "Next Steps:"
log_info "1. Follow the setup instructions to configure your Slack app"
log_info "2. Update your .env file with the Slack credentials"
log_info "3. Run the validation script to verify configuration"
log_info "4. Test the bot functionality in your Slack workspace"
echo
log_warning "IMPORTANT URLS FOR SLACK APP CONFIGURATION:"
log_warning "  Events URL: ${API_GATEWAY_URL}/slack/events"
log_warning "  Interactive URL: ${API_GATEWAY_URL}/slack/interactive"
log_warning "  Commands URL: ${API_GATEWAY_URL}/slack/commands"
echo
log_success "Configuration completed at $(date)"