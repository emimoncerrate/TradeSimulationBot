#!/bin/bash

# =============================================================================
# Jain Global Slack Trading Bot - Advanced Monitoring Setup
# =============================================================================
# This script sets up comprehensive monitoring, alerting, and observability
# for the Slack Trading Bot including custom metrics, alarms, and dashboards.
#
# Usage:
#   ./scripts/setup-monitoring.sh [environment] [region] [email]
#
# Examples:
#   ./scripts/setup-monitoring.sh development us-east-1 admin@jainglobal.com
#   ./scripts/setup-monitoring.sh production us-west-2 alerts@jainglobal.com
# =============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# =============================================================================
# CONFIGURATION
# =============================================================================

ENVIRONMENT=${1:-development}
AWS_REGION=${2:-us-east-1}
ALERT_EMAIL=${3:-""}
STACK_NAME="jain-trading-bot-${ENVIRONMENT}"

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
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    log_error "AWS CLI is not configured"
    exit 1
fi

# =============================================================================
# SNS TOPIC FOR ALERTS
# =============================================================================

log_info "Setting up SNS topic for alerts..."

SNS_TOPIC_NAME="jain-trading-bot-${ENVIRONMENT}-alerts"
SNS_TOPIC_ARN=$(aws sns create-topic \
    --region "$AWS_REGION" \
    --name "$SNS_TOPIC_NAME" \
    --query 'TopicArn' \
    --output text)

log_success "SNS topic created: $SNS_TOPIC_ARN"

# Subscribe email if provided
if [[ -n "$ALERT_EMAIL" ]]; then
    log_info "Subscribing email $ALERT_EMAIL to alerts..."
    aws sns subscribe \
        --region "$AWS_REGION" \
        --topic-arn "$SNS_TOPIC_ARN" \
        --protocol email \
        --notification-endpoint "$ALERT_EMAIL"
    log_warning "Please check your email and confirm the subscription"
fi

# =============================================================================
# CLOUDWATCH ALARMS
# =============================================================================

log_info "Creating CloudWatch alarms..."

# Lambda Function Alarms
aws cloudwatch put-metric-alarm \
    --region "$AWS_REGION" \
    --alarm-name "JainTradingBot-${ENVIRONMENT}-Lambda-Errors" \
    --alarm-description "Lambda function error rate is too high" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=FunctionName,Value="jain-trading-bot-${ENVIRONMENT}-lambda" \
    --alarm-actions "$SNS_TOPIC_ARN" \
    --ok-actions "$SNS_TOPIC_ARN"

aws cloudwatch put-metric-alarm \
    --region "$AWS_REGION" \
    --alarm-name "JainTradingBot-${ENVIRONMENT}-Lambda-Duration" \
    --alarm-description "Lambda function duration is too high" \
    --metric-name Duration \
    --namespace AWS/Lambda \
    --statistic Average \
    --period 300 \
    --evaluation-periods 3 \
    --threshold 25000 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=FunctionName,Value="jain-trading-bot-${ENVIRONMENT}-lambda" \
    --alarm-actions "$SNS_TOPIC_ARN"

aws cloudwatch put-metric-alarm \
    --region "$AWS_REGION" \
    --alarm-name "JainTradingBot-${ENVIRONMENT}-Lambda-Throttles" \
    --alarm-description "Lambda function is being throttled" \
    --metric-name Throttles \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --dimensions Name=FunctionName,Value="jain-trading-bot-${ENVIRONMENT}-lambda" \
    --alarm-actions "$SNS_TOPIC_ARN"

# API Gateway Alarms
aws cloudwatch put-metric-alarm \
    --region "$AWS_REGION" \
    --alarm-name "JainTradingBot-${ENVIRONMENT}-API-5XX-Errors" \
    --alarm-description "API Gateway 5XX error rate is too high" \
    --metric-name 5XXError \
    --namespace AWS/ApiGateway \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=ApiName,Value="jain-trading-bot-${ENVIRONMENT}-api" \
    --alarm-actions "$SNS_TOPIC_ARN"

aws cloudwatch put-metric-alarm \
    --region "$AWS_REGION" \
    --alarm-name "JainTradingBot-${ENVIRONMENT}-API-Latency" \
    --alarm-description "API Gateway latency is too high" \
    --metric-name Latency \
    --namespace AWS/ApiGateway \
    --statistic Average \
    --period 300 \
    --evaluation-periods 3 \
    --threshold 5000 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=ApiName,Value="jain-trading-bot-${ENVIRONMENT}-api" \
    --alarm-actions "$SNS_TOPIC_ARN"

# DynamoDB Alarms
for table in "trades" "positions" "channels"; do
    aws cloudwatch put-metric-alarm \
        --region "$AWS_REGION" \
        --alarm-name "JainTradingBot-${ENVIRONMENT}-DDB-${table}-Throttles" \
        --alarm-description "DynamoDB ${table} table is being throttled" \
        --metric-name ReadThrottledEvents \
        --namespace AWS/DynamoDB \
        --statistic Sum \
        --period 300 \
        --evaluation-periods 1 \
        --threshold 1 \
        --comparison-operator GreaterThanOrEqualToThreshold \
        --dimensions Name=TableName,Value="jain-trading-bot-${ENVIRONMENT}-${table}" \
        --alarm-actions "$SNS_TOPIC_ARN"
done

log_success "CloudWatch alarms created"

# =============================================================================
# CUSTOM METRICS AND DASHBOARD
# =============================================================================

log_info "Creating comprehensive CloudWatch dashboard..."

DASHBOARD_BODY=$(cat << 'EOF'
{
    "widgets": [
        {
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/Lambda", "Invocations", "FunctionName", "LAMBDA_FUNCTION_NAME" ],
                    [ ".", "Errors", ".", "." ],
                    [ ".", "Throttles", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "AWS_REGION",
                "title": "Lambda Invocations & Errors",
                "period": 300,
                "yAxis": {
                    "left": {
                        "min": 0
                    }
                }
            }
        },
        {
            "type": "metric",
            "x": 8,
            "y": 0,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/Lambda", "Duration", "FunctionName", "LAMBDA_FUNCTION_NAME" ],
                    [ ".", "ConcurrentExecutions", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "AWS_REGION",
                "title": "Lambda Performance",
                "period": 300,
                "yAxis": {
                    "left": {
                        "min": 0
                    }
                }
            }
        },
        {
            "type": "metric",
            "x": 16,
            "y": 0,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/ApiGateway", "Count", "ApiName", "API_NAME" ],
                    [ ".", "4XXError", ".", "." ],
                    [ ".", "5XXError", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "AWS_REGION",
                "title": "API Gateway Requests & Errors",
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
                    [ "AWS/ApiGateway", "Latency", "ApiName", "API_NAME" ],
                    [ ".", "IntegrationLatency", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "AWS_REGION",
                "title": "API Gateway Latency",
                "period": 300,
                "yAxis": {
                    "left": {
                        "min": 0
                    }
                }
            }
        },
        {
            "type": "metric",
            "x": 12,
            "y": 6,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "TRADES_TABLE" ],
                    [ ".", "ConsumedWriteCapacityUnits", ".", "." ],
                    [ ".", "ConsumedReadCapacityUnits", "TableName", "POSITIONS_TABLE" ],
                    [ ".", "ConsumedWriteCapacityUnits", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "AWS_REGION",
                "title": "DynamoDB Capacity Usage",
                "period": 300
            }
        },
        {
            "type": "log",
            "x": 0,
            "y": 12,
            "width": 12,
            "height": 6,
            "properties": {
                "query": "SOURCE 'LOG_GROUP_NAME'\n| fields @timestamp, @message\n| filter @message like /ERROR/\n| sort @timestamp desc\n| limit 20",
                "region": "AWS_REGION",
                "title": "Recent Errors",
                "view": "table"
            }
        },
        {
            "type": "log",
            "x": 12,
            "y": 12,
            "width": 12,
            "height": 6,
            "properties": {
                "query": "SOURCE 'LOG_GROUP_NAME'\n| fields @timestamp, @message\n| filter @message like /trade_executed/\n| sort @timestamp desc\n| limit 20",
                "region": "AWS_REGION",
                "title": "Recent Trades",
                "view": "table"
            }
        },
        {
            "type": "metric",
            "x": 0,
            "y": 18,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/DynamoDB", "ItemCount", "TableName", "TRADES_TABLE" ],
                    [ ".", "ItemCount", "TableName", "POSITIONS_TABLE" ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "AWS_REGION",
                "title": "Database Item Counts",
                "period": 3600
            }
        },
        {
            "type": "metric",
            "x": 8,
            "y": 18,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/DynamoDB", "ReadThrottledEvents", "TableName", "TRADES_TABLE" ],
                    [ ".", "WriteThrottledEvents", ".", "." ],
                    [ ".", "ReadThrottledEvents", "TableName", "POSITIONS_TABLE" ],
                    [ ".", "WriteThrottledEvents", ".", "." ]
                ],
                "view": "timeSeries",
                "stacked": false,
                "region": "AWS_REGION",
                "title": "DynamoDB Throttling",
                "period": 300
            }
        },
        {
            "type": "number",
            "x": 16,
            "y": 18,
            "width": 8,
            "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/Lambda", "Invocations", "FunctionName", "LAMBDA_FUNCTION_NAME", { "stat": "Sum" } ]
                ],
                "view": "singleValue",
                "region": "AWS_REGION",
                "title": "Total Invocations (24h)",
                "period": 86400
            }
        }
    ]
}
EOF
)

# Replace placeholders in dashboard JSON
DASHBOARD_BODY=$(echo "$DASHBOARD_BODY" | sed "s/LAMBDA_FUNCTION_NAME/jain-trading-bot-${ENVIRONMENT}-lambda/g")
DASHBOARD_BODY=$(echo "$DASHBOARD_BODY" | sed "s/API_NAME/jain-trading-bot-${ENVIRONMENT}-api/g")
DASHBOARD_BODY=$(echo "$DASHBOARD_BODY" | sed "s/TRADES_TABLE/jain-trading-bot-${ENVIRONMENT}-trades/g")
DASHBOARD_BODY=$(echo "$DASHBOARD_BODY" | sed "s/POSITIONS_TABLE/jain-trading-bot-${ENVIRONMENT}-positions/g")
DASHBOARD_BODY=$(echo "$DASHBOARD_BODY" | sed "s/LOG_GROUP_NAME/\/aws\/lambda\/jain-trading-bot-${ENVIRONMENT}-lambda/g")
DASHBOARD_BODY=$(echo "$DASHBOARD_BODY" | sed "s/AWS_REGION/${AWS_REGION}/g")

# Create the comprehensive dashboard
aws cloudwatch put-dashboard \
    --region "$AWS_REGION" \
    --dashboard-name "JainTradingBot-${ENVIRONMENT}-Comprehensive" \
    --dashboard-body "$DASHBOARD_BODY"

log_success "Comprehensive CloudWatch dashboard created"

# =============================================================================
# LOG INSIGHTS QUERIES
# =============================================================================

log_info "Setting up CloudWatch Logs Insights saved queries..."

# Create saved queries for common investigations
QUERIES=(
    "Trade Executions|SOURCE '/aws/lambda/jain-trading-bot-${ENVIRONMENT}-lambda' | fields @timestamp, @message | filter @message like /trade_executed/ | sort @timestamp desc"
    "Error Analysis|SOURCE '/aws/lambda/jain-trading-bot-${ENVIRONMENT}-lambda' | fields @timestamp, @message, @requestId | filter @message like /ERROR/ | sort @timestamp desc"
    "Performance Issues|SOURCE '/aws/lambda/jain-trading-bot-${ENVIRONMENT}-lambda' | fields @timestamp, @duration, @message | filter @duration > 10000 | sort @duration desc"
    "User Activity|SOURCE '/aws/lambda/jain-trading-bot-${ENVIRONMENT}-lambda' | fields @timestamp, @message | filter @message like /user_id/ | stats count() by bin(5m)"
    "API Errors|SOURCE '/aws/lambda/jain-trading-bot-${ENVIRONMENT}-lambda' | fields @timestamp, @message | filter @message like /status_code/ and @message like /[45][0-9][0-9]/ | sort @timestamp desc"
)

for query in "${QUERIES[@]}"; do
    IFS='|' read -r name query_text <<< "$query"
    # Note: AWS CLI doesn't support creating saved queries directly
    # These would need to be created manually in the console or via SDK
    log_info "Query '$name' ready for manual creation in CloudWatch Logs Insights"
done

# =============================================================================
# HEALTH CHECK ENDPOINT MONITORING
# =============================================================================

log_info "Setting up health check monitoring..."

# Get API Gateway URL
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [[ -n "$API_URL" ]]; then
    # Create Route 53 health check (if Route 53 is being used)
    log_info "API Gateway URL: ${API_URL}/health"
    log_info "Consider setting up Route 53 health checks for: ${API_URL}/health"
    
    # Test the health endpoint
    log_info "Testing health endpoint..."
    if curl -s "${API_URL}/health" > /dev/null; then
        log_success "Health endpoint is responding"
    else
        log_warning "Health endpoint is not responding (this is expected if not deployed yet)"
    fi
fi

# =============================================================================
# SUMMARY
# =============================================================================

log_success "=== MONITORING SETUP COMPLETED ==="
echo
log_info "Environment: $ENVIRONMENT"
log_info "Region: $AWS_REGION"
log_info "SNS Topic: $SNS_TOPIC_ARN"
echo
log_info "Created Alarms:"
log_info "  - Lambda Errors, Duration, Throttles"
log_info "  - API Gateway 5XX Errors, Latency"
log_info "  - DynamoDB Throttling (all tables)"
echo
log_info "Dashboards:"
log_info "  - JainTradingBot-${ENVIRONMENT}-Comprehensive"
echo
log_info "CloudWatch Console:"
log_info "  https://console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:"
echo
if [[ -n "$ALERT_EMAIL" ]]; then
    log_warning "IMPORTANT: Check your email ($ALERT_EMAIL) and confirm the SNS subscription!"
fi
echo
log_success "Monitoring setup completed at $(date)"