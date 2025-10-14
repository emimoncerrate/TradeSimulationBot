#!/bin/bash

# =============================================================================
# Jain Global Slack Trading Bot - Infrastructure Deployment Script
# =============================================================================
# This script deploys the complete AWS infrastructure for the Slack Trading Bot
# including DynamoDB tables, Lambda function, API Gateway, and monitoring.
#
# Usage:
#   ./scripts/deploy-infrastructure.sh [environment] [region]
#
# Examples:
#   ./scripts/deploy-infrastructure.sh development us-east-1
#   ./scripts/deploy-infrastructure.sh production us-west-2
# =============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# =============================================================================
# CONFIGURATION AND VALIDATION
# =============================================================================

# Default values
ENVIRONMENT=${1:-development}
AWS_REGION=${2:-us-east-1}
STACK_NAME="jain-trading-bot-${ENVIRONMENT}"
SAM_CONFIG_FILE="samconfig.toml"

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

# Validate environment parameter
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    log_error "Valid environments: development, staging, production"
    exit 1
fi

# Validate AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    log_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS CLI is not configured. Please run 'aws configure' first."
    exit 1
fi

# Validate SAM CLI is installed
if ! command -v sam &> /dev/null; then
    log_error "SAM CLI is not installed. Please install it first."
    exit 1
fi

# =============================================================================
# ENVIRONMENT VARIABLE VALIDATION
# =============================================================================

log_info "Validating required environment variables..."

# Check for required environment variables
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
    log_error "Please set these variables in your .env file or environment"
    exit 1
fi

# Optional variables with defaults
APPROVED_CHANNELS=${APPROVED_CHANNELS:-""}
BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID:-"anthropic.claude-3-sonnet-20240229-v1:0"}
LOG_LEVEL=${LOG_LEVEL:-"INFO"}

log_success "Environment variables validated"

# =============================================================================
# PRE-DEPLOYMENT CHECKS
# =============================================================================

log_info "Performing pre-deployment checks..."

# Check if stack already exists
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" &> /dev/null; then
    log_warning "Stack $STACK_NAME already exists. This will be an update deployment."
    DEPLOYMENT_TYPE="update"
else
    log_info "Stack $STACK_NAME does not exist. This will be a new deployment."
    DEPLOYMENT_TYPE="create"
fi

# Validate template
log_info "Validating SAM template..."
if ! sam validate --template template.yaml; then
    log_error "SAM template validation failed"
    exit 1
fi
log_success "SAM template is valid"

# Check AWS permissions
log_info "Checking AWS permissions..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
log_info "Deploying to AWS Account: $ACCOUNT_ID"
log_info "Region: $AWS_REGION"

# =============================================================================
# BUILD APPLICATION
# =============================================================================

log_info "Building SAM application..."

# Create build directory if it doesn't exist
mkdir -p .aws-sam/build

# Build the application
if ! sam build --template template.yaml; then
    log_error "SAM build failed"
    exit 1
fi

log_success "Application built successfully"

# =============================================================================
# DEPLOY INFRASTRUCTURE
# =============================================================================

log_info "Deploying infrastructure to $ENVIRONMENT environment..."

# Create parameter overrides
PARAMETER_OVERRIDES=(
    "Environment=$ENVIRONMENT"
    "LogLevel=$LOG_LEVEL"
    "DynamoDBTablePrefix=jain-trading-bot-$ENVIRONMENT"
    "SlackBotToken=$SLACK_BOT_TOKEN"
    "SlackSigningSecret=$SLACK_SIGNING_SECRET"
    "FinnhubApiKey=$FINNHUB_API_KEY"
    "ApprovedChannels=$APPROVED_CHANNELS"
    "BedrockModelId=$BEDROCK_MODEL_ID"
)

# Deploy with SAM
sam deploy \
    --template-file .aws-sam/build/template.yaml \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --parameter-overrides "${PARAMETER_OVERRIDES[@]}" \
    --tags Environment="$ENVIRONMENT" Application="JainTradingBot" \
    --no-fail-on-empty-changeset \
    --resolve-s3

if [[ $? -eq 0 ]]; then
    log_success "Infrastructure deployment completed successfully"
else
    log_error "Infrastructure deployment failed"
    exit 1
fi

# =============================================================================
# POST-DEPLOYMENT CONFIGURATION
# =============================================================================

log_info "Configuring post-deployment settings..."

# Get stack outputs
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text)

LAMBDA_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionArn`].OutputValue' \
    --output text)

TRADES_TABLE=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`TradesTableName`].OutputValue' \
    --output text)

# Initialize approved channels if provided
if [[ -n "$APPROVED_CHANNELS" ]]; then
    log_info "Initializing approved channels in DynamoDB..."
    
    # Split comma-separated channels and add to DynamoDB
    IFS=',' read -ra CHANNELS <<< "$APPROVED_CHANNELS"
    for channel in "${CHANNELS[@]}"; do
        channel=$(echo "$channel" | xargs)  # Trim whitespace
        if [[ -n "$channel" ]]; then
            aws dynamodb put-item \
                --region "$AWS_REGION" \
                --table-name "jain-trading-bot-$ENVIRONMENT-channels" \
                --item "{
                    \"channel_id\": {\"S\": \"$channel\"},
                    \"channel_name\": {\"S\": \"Approved Channel\"},
                    \"is_approved\": {\"BOOL\": true},
                    \"created_by\": {\"S\": \"deployment-script\"},
                    \"created_at\": {\"S\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}
                }" || log_warning "Failed to add channel $channel to DynamoDB"
        fi
    done
    log_success "Approved channels initialized"
fi

# =============================================================================
# CLOUDWATCH DASHBOARD CREATION
# =============================================================================

log_info "Creating CloudWatch dashboard..."

# Create dashboard JSON
DASHBOARD_BODY=$(cat << EOF
{
    "widgets": [
        {
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/Lambda", "Invocations", "FunctionName", "jain-trading-bot-${ENVIRONMENT}-lambda" ],
                    [ ".", "Errors", ".", "." ],
                    [ ".", "Duration", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "${AWS_REGION}",
                "title": "Lambda Function Metrics",
                "period": 300
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/ApiGateway", "Count", "ApiName", "jain-trading-bot-${ENVIRONMENT}-api" ],
                    [ ".", "4XXError", ".", "." ],
                    [ ".", "5XXError", ".", "." ],
                    [ ".", "Latency", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "${AWS_REGION}",
                "title": "API Gateway Metrics",
                "period": 300
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 6,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "jain-trading-bot-${ENVIRONMENT}-trades" ],
                    [ ".", "ConsumedWriteCapacityUnits", ".", "." ],
                    [ ".", "ConsumedReadCapacityUnits", "TableName", "jain-trading-bot-${ENVIRONMENT}-positions" ],
                    [ ".", "ConsumedWriteCapacityUnits", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "${AWS_REGION}",
                "title": "DynamoDB Capacity Metrics",
                "period": 300
            }
        },
        {
            "type": "log",
            "x": 12,
            "y": 6,
            "width": 12,
            "height": 6,
            "properties": {
                "query": "SOURCE '/aws/lambda/jain-trading-bot-${ENVIRONMENT}-lambda'\n| fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 20",
                "region": "${AWS_REGION}",
                "title": "Recent Errors",
                "view": "table"
            }
        }
    ]
}
EOF
)

# Create the dashboard
aws cloudwatch put-dashboard \
    --region "$AWS_REGION" \
    --dashboard-name "JainTradingBot-${ENVIRONMENT}" \
    --dashboard-body "$DASHBOARD_BODY"

log_success "CloudWatch dashboard created: JainTradingBot-${ENVIRONMENT}"

# =============================================================================
# DEPLOYMENT SUMMARY
# =============================================================================

log_success "=== DEPLOYMENT COMPLETED SUCCESSFULLY ==="
echo
log_info "Stack Name: $STACK_NAME"
log_info "Environment: $ENVIRONMENT"
log_info "Region: $AWS_REGION"
log_info "API Gateway URL: $API_URL"
log_info "Lambda Function ARN: $LAMBDA_ARN"
log_info "Trades Table: $TRADES_TABLE"
echo
log_info "CloudWatch Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=JainTradingBot-${ENVIRONMENT}"
echo
log_warning "NEXT STEPS:"
log_warning "1. Configure your Slack app with the API Gateway URL:"
log_warning "   - Events: ${API_URL}/slack/events"
log_warning "   - Interactive: ${API_URL}/slack/interactive"
log_warning "   - Commands: ${API_URL}/slack/commands"
log_warning "2. Test the deployment with: curl ${API_URL}/health"
log_warning "3. Monitor the application using the CloudWatch dashboard"
echo
log_success "Deployment completed at $(date)"