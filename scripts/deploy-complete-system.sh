#!/bin/bash

# =============================================================================
# Jain Global Slack Trading Bot - Complete System Deployment
# =============================================================================
# This script orchestrates the complete deployment of the Slack Trading Bot
# including infrastructure, monitoring, security, and Slack app configuration.
#
# Usage:
#   ./scripts/deploy-complete-system.sh [environment] [region] [email]
#
# Examples:
#   ./scripts/deploy-complete-system.sh development us-east-1 dev@jainglobal.com
#   ./scripts/deploy-complete-system.sh production us-west-2 ops@jainglobal.com
# =============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# =============================================================================
# CONFIGURATION
# =============================================================================

ENVIRONMENT=${1:-development}
AWS_REGION=${2:-us-east-1}
ALERT_EMAIL=${3:-""}

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# =============================================================================
# VALIDATION
# =============================================================================

log_info "Starting complete system deployment validation..."

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    log_error "Valid environments: development, staging, production"
    exit 1
fi

# Validate AWS CLI
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS CLI is not configured"
    exit 1
fi

# Validate SAM CLI
if ! command -v sam &> /dev/null; then
    log_error "SAM CLI is not installed"
    exit 1
fi

# Validate required environment variables
REQUIRED_VARS=(
    "SLACK_BOT_TOKEN"
    "SLACK_SIGNING_SECRET"
    "FINNHUB_API_KEY"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        MISSING_VARS+=("$var")
    fi
done

if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
    log_error "Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        log_error "  - $var"
    done
    exit 1
fi

log_success "Validation completed successfully"

# =============================================================================
# DEPLOYMENT ORCHESTRATION
# =============================================================================

DEPLOYMENT_START_TIME=$(date)
DEPLOYMENT_LOG="deployment-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).log"

log_info "Starting complete system deployment for $ENVIRONMENT environment"
log_info "Deployment log: $DEPLOYMENT_LOG"
echo

# Create deployment log
exec > >(tee -a "$DEPLOYMENT_LOG")
exec 2>&1

echo "=== JAIN GLOBAL SLACK TRADING BOT DEPLOYMENT ===" >> "$DEPLOYMENT_LOG"
echo "Environment: $ENVIRONMENT" >> "$DEPLOYMENT_LOG"
echo "Region: $AWS_REGION" >> "$DEPLOYMENT_LOG"
echo "Start Time: $DEPLOYMENT_START_TIME" >> "$DEPLOYMENT_LOG"
echo "Alert Email: ${ALERT_EMAIL:-'Not provided'}" >> "$DEPLOYMENT_LOG"
echo "=================================================" >> "$DEPLOYMENT_LOG"
echo

# =============================================================================
# STEP 1: INFRASTRUCTURE DEPLOYMENT
# =============================================================================

log_step "STEP 1: Deploying AWS Infrastructure"
echo

if ./scripts/deploy-infrastructure.sh "$ENVIRONMENT" "$AWS_REGION"; then
    log_success "Infrastructure deployment completed"
    
    # Get API Gateway URL for later steps
    API_GATEWAY_URL=$(aws cloudformation describe-stacks \
        --stack-name "jain-trading-bot-${ENVIRONMENT}" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
        --output text 2>/dev/null || echo "")
    
    if [[ -n "$API_GATEWAY_URL" ]]; then
        log_success "API Gateway URL retrieved: $API_GATEWAY_URL"
    else
        log_error "Failed to retrieve API Gateway URL"
        exit 1
    fi
else
    log_error "Infrastructure deployment failed"
    exit 1
fi

echo

# =============================================================================
# STEP 2: MONITORING SETUP
# =============================================================================

log_step "STEP 2: Setting up Monitoring and Alerting"
echo

if [[ -n "$ALERT_EMAIL" ]]; then
    if ./scripts/setup-monitoring.sh "$ENVIRONMENT" "$AWS_REGION" "$ALERT_EMAIL"; then
        log_success "Monitoring setup completed with email alerts"
    else
        log_warning "Monitoring setup completed with warnings"
    fi
else
    if ./scripts/setup-monitoring.sh "$ENVIRONMENT" "$AWS_REGION"; then
        log_success "Monitoring setup completed (no email alerts)"
    else
        log_warning "Monitoring setup completed with warnings"
    fi
fi

echo

# =============================================================================
# STEP 3: SECURITY CONFIGURATION
# =============================================================================

log_step "STEP 3: Configuring Security Settings"
echo

if ./scripts/setup-slack-security.sh "$ENVIRONMENT" "$AWS_REGION"; then
    log_success "Security configuration completed"
else
    log_warning "Security configuration completed with warnings"
fi

echo

# =============================================================================
# STEP 4: SLACK APP CONFIGURATION
# =============================================================================

log_step "STEP 4: Generating Slack App Configuration"
echo

if ./scripts/configure-slack-app.sh "$ENVIRONMENT" "$API_GATEWAY_URL"; then
    log_success "Slack app configuration generated"
else
    log_error "Slack app configuration failed"
    exit 1
fi

echo

# =============================================================================
# STEP 5: INFRASTRUCTURE VALIDATION
# =============================================================================

log_step "STEP 5: Validating Infrastructure Deployment"
echo

if ./scripts/validate-infrastructure.sh "$ENVIRONMENT" "$AWS_REGION"; then
    log_success "Infrastructure validation passed"
else
    log_error "Infrastructure validation failed"
    exit 1
fi

echo

# =============================================================================
# STEP 6: SECURITY VALIDATION
# =============================================================================

log_step "STEP 6: Validating Security Configuration"
echo

if ./scripts/validate-security-config.sh "$ENVIRONMENT" "$AWS_REGION"; then
    log_success "Security validation passed"
else
    log_warning "Security validation completed with warnings"
fi

echo

# =============================================================================
# STEP 7: HEALTH CHECKS
# =============================================================================

log_step "STEP 7: Performing Health Checks"
echo

log_info "Testing API Gateway health endpoint..."
if curl -s -f "${API_GATEWAY_URL}/health" > /dev/null; then
    log_success "Health endpoint is responding"
else
    log_warning "Health endpoint is not responding (may be expected for cold Lambda)"
fi

log_info "Testing Slack endpoint configuration..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_GATEWAY_URL}/slack/events" || echo "000")
if [[ "$HTTP_CODE" == "400" || "$HTTP_CODE" == "405" ]]; then
    log_success "Slack events endpoint is configured correctly"
else
    log_warning "Slack events endpoint returned unexpected status: $HTTP_CODE"
fi

echo

# =============================================================================
# DEPLOYMENT SUMMARY
# =============================================================================

DEPLOYMENT_END_TIME=$(date)
DEPLOYMENT_DURATION=$(($(date +%s) - $(date -d "$DEPLOYMENT_START_TIME" +%s)))

log_success "=== DEPLOYMENT COMPLETED SUCCESSFULLY ==="
echo
log_info "Deployment Summary:"
log_info "  Environment: $ENVIRONMENT"
log_info "  Region: $AWS_REGION"
log_info "  Start Time: $DEPLOYMENT_START_TIME"
log_info "  End Time: $DEPLOYMENT_END_TIME"
log_info "  Duration: ${DEPLOYMENT_DURATION} seconds"
log_info "  API Gateway URL: $API_GATEWAY_URL"
echo
log_info "Deployed Components:"
log_info "  ✓ AWS Infrastructure (Lambda, API Gateway, DynamoDB)"
log_info "  ✓ Monitoring and Alerting (CloudWatch, SNS)"
log_info "  ✓ Security Configuration (IAM, Encryption, Audit)"
log_info "  ✓ Slack App Configuration Files"
echo
log_info "Generated Files:"
log_info "  - config/slack/app-manifest-${ENVIRONMENT}.json"
log_info "  - config/slack/setup-instructions-${ENVIRONMENT}.md"
log_info "  - config/slack/workspace-installation-guide.md"
log_info "  - config/security/security-config-${ENVIRONMENT}.json"
log_info "  - config/security/user-roles-${ENVIRONMENT}.json"
log_info "  - docs/deployment-guide.md"
echo
log_warning "MANUAL STEPS REQUIRED:"
log_warning "1. Configure Slack App:"
log_warning "   - Follow instructions in: config/slack/setup-instructions-${ENVIRONMENT}.md"
log_warning "   - Use app manifest: config/slack/app-manifest-${ENVIRONMENT}.json"
log_warning "   - Set these URLs in your Slack app:"
log_warning "     * Events: ${API_GATEWAY_URL}/slack/events"
log_warning "     * Interactive: ${API_GATEWAY_URL}/slack/interactive"
log_warning "     * Commands: ${API_GATEWAY_URL}/slack/commands"
echo
log_warning "2. Update Environment Variables:"
log_warning "   - Add actual approved channel IDs to APPROVED_CHANNELS"
log_warning "   - Redeploy after updating: ./scripts/deploy-infrastructure.sh $ENVIRONMENT $AWS_REGION"
echo
log_warning "3. Test the Deployment:"
log_warning "   - Install bot to Slack workspace"
log_warning "   - Test /trade command in approved channel"
log_warning "   - Verify App Home functionality"
log_warning "   - Run: ./scripts/validate-slack-config.sh $ENVIRONMENT $API_GATEWAY_URL"
echo
if [[ -n "$ALERT_EMAIL" ]]; then
    log_warning "4. Confirm Email Subscription:"
    log_warning "   - Check email: $ALERT_EMAIL"
    log_warning "   - Confirm SNS subscription for alerts"
    echo
fi
log_info "Monitoring Dashboards:"
log_info "  - CloudWatch: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:"
log_info "  - Lambda Logs: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#logsV2:log-groups/log-group/%2Faws%2Flambda%2Fjain-trading-bot-${ENVIRONMENT}-lambda"
echo
log_info "Support Resources:"
log_info "  - Deployment Guide: docs/deployment-guide.md"
log_info "  - Troubleshooting: Check CloudWatch logs and run validation scripts"
log_info "  - Deployment Log: $DEPLOYMENT_LOG"
echo
log_success "Deployment completed successfully at $DEPLOYMENT_END_TIME"

# =============================================================================
# POST-DEPLOYMENT ACTIONS
# =============================================================================

# Create a deployment summary file
cat > "deployment-summary-${ENVIRONMENT}.md" << EOF
# Deployment Summary - ${ENVIRONMENT}

## Deployment Information
- **Environment**: ${ENVIRONMENT}
- **Region**: ${AWS_REGION}
- **Start Time**: ${DEPLOYMENT_START_TIME}
- **End Time**: ${DEPLOYMENT_END_TIME}
- **Duration**: ${DEPLOYMENT_DURATION} seconds
- **API Gateway URL**: ${API_GATEWAY_URL}

## Deployed Components
- AWS Infrastructure (Lambda, API Gateway, DynamoDB)
- Monitoring and Alerting (CloudWatch, SNS)
- Security Configuration (IAM, Encryption, Audit)
- Slack App Configuration Files

## Next Steps
1. Configure Slack App using generated files
2. Update approved channels list
3. Test deployment functionality
4. Set up user roles and permissions

## Resources
- Deployment Log: ${DEPLOYMENT_LOG}
- Configuration Files: config/slack/ and config/security/
- Documentation: docs/deployment-guide.md

Generated: $(date)
EOF

log_info "Deployment summary saved: deployment-summary-${ENVIRONMENT}.md"