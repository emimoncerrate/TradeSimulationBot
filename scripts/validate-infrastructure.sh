#!/bin/bash

# =============================================================================
# Jain Global Slack Trading Bot - Infrastructure Validation Script
# =============================================================================
# This script validates the deployed AWS infrastructure to ensure all
# components are properly configured and functioning correctly.
#
# Usage:
#   ./scripts/validate-infrastructure.sh [environment] [region]
#
# Examples:
#   ./scripts/validate-infrastructure.sh development us-east-1
#   ./scripts/validate-infrastructure.sh production us-west-2
# =============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# =============================================================================
# CONFIGURATION
# =============================================================================

ENVIRONMENT=${1:-development}
AWS_REGION=${2:-us-east-1}
STACK_NAME="jain-trading-bot-${ENVIRONMENT}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters for validation results
PASSED=0
FAILED=0
WARNINGS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

validate_stack_exists() {
    log_info "Validating CloudFormation stack exists..."
    
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" &> /dev/null; then
        STACK_STATUS=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION" \
            --query 'Stacks[0].StackStatus' \
            --output text)
        
        if [[ "$STACK_STATUS" == "CREATE_COMPLETE" || "$STACK_STATUS" == "UPDATE_COMPLETE" ]]; then
            log_success "CloudFormation stack exists and is in good state: $STACK_STATUS"
        else
            log_error "CloudFormation stack exists but in bad state: $STACK_STATUS"
        fi
    else
        log_error "CloudFormation stack does not exist: $STACK_NAME"
    fi
}

validate_lambda_function() {
    log_info "Validating Lambda function..."
    
    FUNCTION_NAME="jain-trading-bot-${ENVIRONMENT}-lambda"
    
    if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" &> /dev/null; then
        # Check function state
        FUNCTION_STATE=$(aws lambda get-function \
            --function-name "$FUNCTION_NAME" \
            --region "$AWS_REGION" \
            --query 'Configuration.State' \
            --output text)
        
        if [[ "$FUNCTION_STATE" == "Active" ]]; then
            log_success "Lambda function is active: $FUNCTION_NAME"
        else
            log_error "Lambda function is not active: $FUNCTION_STATE"
        fi
        
        # Check runtime
        RUNTIME=$(aws lambda get-function \
            --function-name "$FUNCTION_NAME" \
            --region "$AWS_REGION" \
            --query 'Configuration.Runtime' \
            --output text)
        
        if [[ "$RUNTIME" == "python3.11" ]]; then
            log_success "Lambda runtime is correct: $RUNTIME"
        else
            log_warning "Lambda runtime might be outdated: $RUNTIME"
        fi
        
        # Check timeout
        TIMEOUT=$(aws lambda get-function \
            --function-name "$FUNCTION_NAME" \
            --region "$AWS_REGION" \
            --query 'Configuration.Timeout' \
            --output text)
        
        if [[ "$TIMEOUT" -ge 30 ]]; then
            log_success "Lambda timeout is appropriate: ${TIMEOUT}s"
        else
            log_warning "Lambda timeout might be too low: ${TIMEOUT}s"
        fi
        
    else
        log_error "Lambda function does not exist: $FUNCTION_NAME"
    fi
}

validate_api_gateway() {
    log_info "Validating API Gateway..."
    
    # Get API Gateway URL from stack outputs
    API_URL=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
        --output text 2>/dev/null || echo "")
    
    if [[ -n "$API_URL" ]]; then
        log_success "API Gateway URL found: $API_URL"
        
        # Test health endpoint
        log_info "Testing health endpoint..."
        if curl -s -f "${API_URL}/health" > /dev/null; then
            log_success "Health endpoint is responding"
        else
            log_warning "Health endpoint is not responding (may be expected if Lambda is cold)"
        fi
        
        # Test HTTPS
        if [[ "$API_URL" == https://* ]]; then
            log_success "API Gateway is using HTTPS"
        else
            log_error "API Gateway is not using HTTPS"
        fi
        
    else
        log_error "API Gateway URL not found in stack outputs"
    fi
}

validate_dynamodb_tables() {
    log_info "Validating DynamoDB tables..."
    
    TABLES=("trades" "positions" "channels")
    
    for table_suffix in "${TABLES[@]}"; do
        TABLE_NAME="jain-trading-bot-${ENVIRONMENT}-${table_suffix}"
        
        if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$AWS_REGION" &> /dev/null; then
            # Check table status
            TABLE_STATUS=$(aws dynamodb describe-table \
                --table-name "$TABLE_NAME" \
                --region "$AWS_REGION" \
                --query 'Table.TableStatus' \
                --output text)
            
            if [[ "$TABLE_STATUS" == "ACTIVE" ]]; then
                log_success "DynamoDB table is active: $TABLE_NAME"
            else
                log_error "DynamoDB table is not active: $TABLE_NAME ($TABLE_STATUS)"
            fi
            
            # Check encryption
            SSE_STATUS=$(aws dynamodb describe-table \
                --table-name "$TABLE_NAME" \
                --region "$AWS_REGION" \
                --query 'Table.SSEDescription.Status' \
                --output text 2>/dev/null || echo "NONE")
            
            if [[ "$SSE_STATUS" == "ENABLED" ]]; then
                log_success "DynamoDB table encryption is enabled: $TABLE_NAME"
            else
                log_warning "DynamoDB table encryption is not enabled: $TABLE_NAME"
            fi
            
            # Check point-in-time recovery for production
            if [[ "$ENVIRONMENT" == "production" ]]; then
                PITR_STATUS=$(aws dynamodb describe-continuous-backups \
                    --table-name "$TABLE_NAME" \
                    --region "$AWS_REGION" \
                    --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus' \
                    --output text 2>/dev/null || echo "DISABLED")
                
                if [[ "$PITR_STATUS" == "ENABLED" ]]; then
                    log_success "Point-in-time recovery is enabled: $TABLE_NAME"
                else
                    log_warning "Point-in-time recovery is not enabled: $TABLE_NAME"
                fi
            fi
            
        else
            log_error "DynamoDB table does not exist: $TABLE_NAME"
        fi
    done
}

validate_iam_permissions() {
    log_info "Validating IAM permissions..."
    
    FUNCTION_NAME="jain-trading-bot-${ENVIRONMENT}-lambda"
    
    # Get Lambda function role
    ROLE_ARN=$(aws lambda get-function \
        --function-name "$FUNCTION_NAME" \
        --region "$AWS_REGION" \
        --query 'Configuration.Role' \
        --output text 2>/dev/null || echo "")
    
    if [[ -n "$ROLE_ARN" ]]; then
        ROLE_NAME=$(echo "$ROLE_ARN" | cut -d'/' -f2)
        log_success "Lambda execution role found: $ROLE_NAME"
        
        # Check if role has DynamoDB permissions
        if aws iam list-attached-role-policies --role-name "$ROLE_NAME" --query 'AttachedPolicies[?contains(PolicyName, `DynamoDB`)]' --output text | grep -q .; then
            log_success "Lambda role has DynamoDB permissions"
        else
            log_warning "Lambda role might be missing DynamoDB permissions"
        fi
        
        # Check if role has Bedrock permissions
        if aws iam list-role-policies --role-name "$ROLE_NAME" --query 'PolicyNames' --output text | grep -q .; then
            log_success "Lambda role has inline policies (likely including Bedrock)"
        else
            log_warning "Lambda role might be missing Bedrock permissions"
        fi
        
    else
        log_error "Lambda execution role not found"
    fi
}

validate_cloudwatch_logs() {
    log_info "Validating CloudWatch Logs..."
    
    LOG_GROUPS=(
        "/aws/lambda/jain-trading-bot-${ENVIRONMENT}-lambda"
        "/aws/apigateway/jain-trading-bot-${ENVIRONMENT}-api"
    )
    
    for log_group in "${LOG_GROUPS[@]}"; do
        if aws logs describe-log-groups --log-group-name-prefix "$log_group" --region "$AWS_REGION" --query 'logGroups[0]' --output text &> /dev/null; then
            log_success "CloudWatch log group exists: $log_group"
            
            # Check retention policy
            RETENTION=$(aws logs describe-log-groups \
                --log-group-name-prefix "$log_group" \
                --region "$AWS_REGION" \
                --query 'logGroups[0].retentionInDays' \
                --output text 2>/dev/null || echo "null")
            
            if [[ "$RETENTION" != "null" && "$RETENTION" != "None" ]]; then
                log_success "Log retention is configured: $log_group (${RETENTION} days)"
            else
                log_warning "Log retention is not configured: $log_group"
            fi
            
        else
            log_error "CloudWatch log group does not exist: $log_group"
        fi
    done
}

validate_monitoring() {
    log_info "Validating monitoring setup..."
    
    # Check for CloudWatch alarms
    ALARM_COUNT=$(aws cloudwatch describe-alarms \
        --alarm-name-prefix "JainTradingBot-${ENVIRONMENT}" \
        --region "$AWS_REGION" \
        --query 'length(MetricAlarms)' \
        --output text 2>/dev/null || echo "0")
    
    if [[ "$ALARM_COUNT" -gt 0 ]]; then
        log_success "CloudWatch alarms are configured: $ALARM_COUNT alarms"
    else
        log_warning "No CloudWatch alarms found"
    fi
    
    # Check for dashboards
    if aws cloudwatch list-dashboards --region "$AWS_REGION" --query "DashboardEntries[?contains(DashboardName, 'JainTradingBot-${ENVIRONMENT}')]" --output text | grep -q .; then
        log_success "CloudWatch dashboard exists"
    else
        log_warning "CloudWatch dashboard not found"
    fi
}

validate_security() {
    log_info "Validating security configuration..."
    
    # Check KMS key for production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        KMS_KEY_ID=$(aws cloudformation describe-stacks \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION" \
            --query 'Stacks[0].Outputs[?OutputKey==`KMSKeyId`].OutputValue' \
            --output text 2>/dev/null || echo "")
        
        if [[ -n "$KMS_KEY_ID" && "$KMS_KEY_ID" != "None" ]]; then
            log_success "KMS key is configured for production"
        else
            log_warning "KMS key not found for production environment"
        fi
    fi
    
    # Check API Gateway throttling
    API_ID=$(aws apigateway get-rest-apis \
        --region "$AWS_REGION" \
        --query "items[?name=='jain-trading-bot-${ENVIRONMENT}-api'].id" \
        --output text 2>/dev/null || echo "")
    
    if [[ -n "$API_ID" ]]; then
        THROTTLE_SETTINGS=$(aws apigateway get-stage \
            --rest-api-id "$API_ID" \
            --stage-name "$ENVIRONMENT" \
            --region "$AWS_REGION" \
            --query 'throttleSettings' \
            --output text 2>/dev/null || echo "")
        
        if [[ -n "$THROTTLE_SETTINGS" && "$THROTTLE_SETTINGS" != "None" ]]; then
            log_success "API Gateway throttling is configured"
        else
            log_warning "API Gateway throttling might not be configured"
        fi
    fi
}

validate_environment_variables() {
    log_info "Validating Lambda environment variables..."
    
    FUNCTION_NAME="jain-trading-bot-${ENVIRONMENT}-lambda"
    
    REQUIRED_VARS=(
        "SLACK_BOT_TOKEN"
        "SLACK_SIGNING_SECRET"
        "FINNHUB_API_KEY"
        "TRADES_TABLE_NAME"
        "POSITIONS_TABLE_NAME"
        "CHANNELS_TABLE_NAME"
    )
    
    ENV_VARS=$(aws lambda get-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --region "$AWS_REGION" \
        --query 'Environment.Variables' \
        --output json 2>/dev/null || echo "{}")
    
    for var in "${REQUIRED_VARS[@]}"; do
        if echo "$ENV_VARS" | jq -r ".$var" | grep -q "null"; then
            log_error "Missing environment variable: $var"
        else
            log_success "Environment variable is set: $var"
        fi
    done
}

# =============================================================================
# MAIN VALIDATION EXECUTION
# =============================================================================

log_info "Starting infrastructure validation for $ENVIRONMENT environment in $AWS_REGION"
echo

# Run all validations
validate_stack_exists
validate_lambda_function
validate_api_gateway
validate_dynamodb_tables
validate_iam_permissions
validate_cloudwatch_logs
validate_monitoring
validate_security
validate_environment_variables

# =============================================================================
# SUMMARY
# =============================================================================

echo
log_info "=== VALIDATION SUMMARY ==="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo

if [[ $FAILED -eq 0 ]]; then
    log_success "Infrastructure validation completed successfully!"
    if [[ $WARNINGS -gt 0 ]]; then
        log_warning "Please review the warnings above"
    fi
    exit 0
else
    log_error "Infrastructure validation failed with $FAILED errors"
    log_error "Please fix the issues above before proceeding"
    exit 1
fi