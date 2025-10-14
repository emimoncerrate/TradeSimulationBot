#!/bin/bash

# =============================================================================
# AWS Services Setup Script for Jain Global Trading Bot
# =============================================================================
# This script sets up all required AWS services for the trading bot:
# - DynamoDB tables
# - IAM roles and policies
# - Lambda function preparation
# - CloudWatch log groups
# - API Gateway (optional)
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
TABLE_PREFIX=${DYNAMODB_TABLE_PREFIX:-jain-trading-bot}
LAMBDA_FUNCTION_NAME=${AWS_LAMBDA_FUNCTION_NAME:-jain-trading-bot-lambda}
LOG_GROUP_NAME="/aws/lambda/${LAMBDA_FUNCTION_NAME}"

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

# Check if AWS CLI is installed and configured
check_aws_cli() {
    log_info "Checking AWS CLI installation and configuration..."
    
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first:"
        echo "  macOS: brew install awscli"
        echo "  Linux: sudo apt-get install awscli"
        echo "  Or visit: https://aws.amazon.com/cli/"
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    local user_arn=$(aws sts get-caller-identity --query Arn --output text)
    
    log_success "AWS CLI configured successfully"
    log_info "Account ID: ${account_id}"
    log_info "User/Role: ${user_arn}"
    log_info "Region: ${AWS_REGION}"
}

# Create DynamoDB tables
create_dynamodb_tables() {
    log_info "Creating DynamoDB tables..."
    
    # Define tables with their schemas
    local tables=(
        "${TABLE_PREFIX}-trades:user_id:S,trade_id:S"
        "${TABLE_PREFIX}-positions:user_id:S,symbol:S"
        "${TABLE_PREFIX}-users:user_id:S"
        "${TABLE_PREFIX}-channels:channel_id:S"
        "${TABLE_PREFIX}-portfolios:user_id:S"
        "${TABLE_PREFIX}-audit:audit_id:S"
    )
    
    for table_entry in "${tables[@]}"; do
        local table_name=$(echo $table_entry | cut -d':' -f1)
        local key_schema=$(echo $table_entry | cut -d':' -f2-)
        local hash_key=$(echo $key_schema | cut -d',' -f1 | cut -d':' -f1)
        local hash_type=$(echo $key_schema | cut -d',' -f1 | cut -d':' -f2)
        
        # Check if table already exists
        if aws dynamodb describe-table --table-name "$table_name" --region "$AWS_REGION" &> /dev/null; then
            log_warning "Table $table_name already exists, skipping..."
            continue
        fi
        
        log_info "Creating table: $table_name"
        
        # Build key schema
        local key_schema_json="[{\"AttributeName\":\"$hash_key\",\"KeyType\":\"HASH\"}"
        local attribute_definitions="[{\"AttributeName\":\"$hash_key\",\"AttributeType\":\"$hash_type\"}"
        
        # Check if there's a range key
        if [[ $key_schema == *","* ]]; then
            local range_key=$(echo $key_schema | cut -d',' -f2 | cut -d':' -f1)
            local range_type=$(echo $key_schema | cut -d',' -f2 | cut -d':' -f2)
            key_schema_json+=",{\"AttributeName\":\"$range_key\",\"KeyType\":\"RANGE\"}"
            attribute_definitions+=",{\"AttributeName\":\"$range_key\",\"AttributeType\":\"$range_type\"}"
        fi
        
        key_schema_json+="]"
        attribute_definitions+="]"
        
        # Create table
        aws dynamodb create-table \
            --table-name "$table_name" \
            --key-schema "$key_schema_json" \
            --attribute-definitions "$attribute_definitions" \
            --billing-mode PAY_PER_REQUEST \
            --region "$AWS_REGION" \
            --tags Key=Project,Value=JainTradingBot Key=Environment,Value=production \
            > /dev/null
        
        log_success "Table $table_name created successfully"
    done
    
    # Wait for tables to be active
    log_info "Waiting for tables to become active..."
    for table_entry in "${tables[@]}"; do
        local table_name=$(echo $table_entry | cut -d':' -f1)
        aws dynamodb wait table-exists --table-name "$table_name" --region "$AWS_REGION"
        log_success "Table $table_name is now active"
    done
}

# Create IAM role for Lambda
create_iam_role() {
    log_info "Creating IAM role for Lambda function..."
    
    local role_name="${LAMBDA_FUNCTION_NAME}-role"
    
    # Check if role already exists
    if aws iam get-role --role-name "$role_name" &> /dev/null; then
        log_warning "IAM role $role_name already exists, skipping creation..."
        return
    fi
    
    # Trust policy for Lambda
    local trust_policy='{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }'
    
    # Create role
    aws iam create-role \
        --role-name "$role_name" \
        --assume-role-policy-document "$trust_policy" \
        --description "IAM role for Jain Trading Bot Lambda function" \
        > /dev/null
    
    log_success "IAM role $role_name created"
    
    # Attach basic Lambda execution policy
    aws iam attach-role-policy \
        --role-name "$role_name" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    
    log_success "Attached basic Lambda execution policy"
    
    # Create custom policy for DynamoDB and Bedrock access
    local policy_name="${LAMBDA_FUNCTION_NAME}-policy"
    local custom_policy='{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchGetItem",
                    "dynamodb:BatchWriteItem"
                ],
                "Resource": [
                    "arn:aws:dynamodb:'$AWS_REGION':*:table/'$TABLE_PREFIX'-*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:ListFoundationModels"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:'$AWS_REGION':*:*"
            }
        ]
    }'
    
    # Create and attach custom policy
    aws iam create-policy \
        --policy-name "$policy_name" \
        --policy-document "$custom_policy" \
        --description "Custom policy for Jain Trading Bot Lambda function" \
        > /dev/null
    
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    aws iam attach-role-policy \
        --role-name "$role_name" \
        --policy-arn "arn:aws:iam::${account_id}:policy/${policy_name}"
    
    log_success "Created and attached custom policy $policy_name"
}

# Create CloudWatch log group
create_log_group() {
    log_info "Creating CloudWatch log group..."
    
    # Check if log group already exists
    if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_NAME" --region "$AWS_REGION" | grep -q "$LOG_GROUP_NAME"; then
        log_warning "Log group $LOG_GROUP_NAME already exists, skipping..."
        return
    fi
    
    aws logs create-log-group \
        --log-group-name "$LOG_GROUP_NAME" \
        --region "$AWS_REGION"
    
    # Set retention policy (30 days for cost optimization)
    aws logs put-retention-policy \
        --log-group-name "$LOG_GROUP_NAME" \
        --retention-in-days 30 \
        --region "$AWS_REGION"
    
    log_success "CloudWatch log group $LOG_GROUP_NAME created with 30-day retention"
}

# Generate updated .env file with real AWS credentials
update_env_file() {
    log_info "Updating .env file with AWS configuration..."
    
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    local access_key_id=$(aws configure get aws_access_key_id)
    local secret_access_key=$(aws configure get aws_secret_access_key)
    
    # Backup existing .env
    if [ -f .env ]; then
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        log_info "Backed up existing .env file"
    fi
    
    # Update AWS configuration in .env
    sed -i.bak \
        -e "s/AWS_ACCESS_KEY_ID=.*/AWS_ACCESS_KEY_ID=${access_key_id}/" \
        -e "s/AWS_SECRET_ACCESS_KEY=.*/AWS_SECRET_ACCESS_KEY=${secret_access_key}/" \
        -e "s/AWS_REGION=.*/AWS_REGION=${AWS_REGION}/" \
        -e "s/DYNAMODB_TABLE_PREFIX=.*/DYNAMODB_TABLE_PREFIX=${TABLE_PREFIX}/" \
        -e "s/AWS_LAMBDA_FUNCTION_NAME=.*/AWS_LAMBDA_FUNCTION_NAME=${LAMBDA_FUNCTION_NAME}/" \
        -e "s/CLOUDWATCH_LOG_GROUP=.*/CLOUDWATCH_LOG_GROUP=${LOG_GROUP_NAME}/" \
        .env
    
    rm .env.bak
    
    log_success "Updated .env file with AWS configuration"
    log_warning "Make sure to never commit your .env file to version control!"
}

# Test AWS services
test_aws_services() {
    log_info "Testing AWS services connectivity..."
    
    # Test DynamoDB
    log_info "Testing DynamoDB access..."
    local test_table="${TABLE_PREFIX}-users"
    if aws dynamodb describe-table --table-name "$test_table" --region "$AWS_REGION" &> /dev/null; then
        log_success "DynamoDB access confirmed"
    else
        log_error "DynamoDB access failed"
        return 1
    fi
    
    # Test Bedrock (if available in region)
    log_info "Testing Bedrock access..."
    if aws bedrock list-foundation-models --region "$AWS_REGION" &> /dev/null; then
        log_success "Bedrock access confirmed"
    else
        log_warning "Bedrock access failed - may not be available in $AWS_REGION"
        log_info "Consider using us-east-1 or us-west-2 for Bedrock access"
    fi
    
    # Test CloudWatch Logs
    log_info "Testing CloudWatch Logs access..."
    if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_NAME" --region "$AWS_REGION" &> /dev/null; then
        log_success "CloudWatch Logs access confirmed"
    else
        log_error "CloudWatch Logs access failed"
        return 1
    fi
}

# Display cost estimates
show_cost_estimates() {
    log_info "AWS Cost Estimates (Monthly):"
    echo ""
    echo "┌─────────────────────┬──────────────────┬─────────────┐"
    echo "│ Service             │ Usage Estimate   │ Cost (USD)  │"
    echo "├─────────────────────┼──────────────────┼─────────────┤"
    echo "│ DynamoDB            │ 1M read/write    │ ~\$1.25      │"
    echo "│ Bedrock (Claude)    │ 100K tokens/day  │ ~\$9.00      │"
    echo "│ Lambda              │ 100K requests    │ ~\$0.20      │"
    echo "│ CloudWatch Logs     │ 1GB logs         │ ~\$0.50      │"
    echo "│ API Gateway         │ 100K requests    │ ~\$0.35      │"
    echo "├─────────────────────┼──────────────────┼─────────────┤"
    echo "│ Total Estimated     │                  │ ~\$11.30     │"
    echo "└─────────────────────┴──────────────────┴─────────────┘"
    echo ""
    log_info "Actual costs may vary based on usage patterns."
    log_info "DynamoDB uses on-demand pricing for cost optimization."
}

# Main execution
main() {
    echo "============================================================================="
    echo "🚀 AWS Services Setup for Jain Global Trading Bot"
    echo "============================================================================="
    echo ""
    
    # Pre-flight checks
    check_aws_cli
    
    echo ""
    log_info "This script will create the following AWS resources:"
    log_info "• 6 DynamoDB tables for data storage"
    log_info "• IAM role and policies for Lambda execution"
    log_info "• CloudWatch log group for monitoring"
    log_info "• Update your .env file with real AWS credentials"
    echo ""
    
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Setup cancelled by user"
        exit 0
    fi
    
    echo ""
    log_info "Starting AWS services setup..."
    echo ""
    
    # Execute setup steps
    create_dynamodb_tables
    echo ""
    
    create_iam_role
    echo ""
    
    create_log_group
    echo ""
    
    update_env_file
    echo ""
    
    test_aws_services
    echo ""
    
    show_cost_estimates
    echo ""
    
    log_success "🎉 AWS services setup completed successfully!"
    echo ""
    log_info "Next steps:"
    log_info "1. Test your bot locally: python app.py"
    log_info "2. Deploy to Lambda: ./scripts/deploy-lambda.sh"
    log_info "3. Monitor costs in AWS Console"
    echo ""
    log_warning "Remember: Your .env file now contains real AWS credentials."
    log_warning "Never commit this file to version control!"
}

# Run main function
main "$@"