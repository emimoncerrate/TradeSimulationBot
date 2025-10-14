#!/bin/bash

# =============================================================================
# Lambda Deployment Script for Jain Global Trading Bot
# =============================================================================
# This script packages and deploys the trading bot to AWS Lambda
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
LAMBDA_FUNCTION_NAME=${AWS_LAMBDA_FUNCTION_NAME:-jain-trading-bot-lambda}
DEPLOYMENT_PACKAGE="lambda-deployment.zip"

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

# Create deployment package
create_deployment_package() {
    log_info "Creating Lambda deployment package..."
    
    # Clean up previous package
    rm -f "$DEPLOYMENT_PACKAGE"
    
    # Create temporary directory
    local temp_dir=$(mktemp -d)
    
    # Copy application files
    cp -r . "$temp_dir/"
    cd "$temp_dir"
    
    # Remove unnecessary files
    rm -rf .git .kiro __pycache__ *.log tests/ docs/ scripts/
    rm -f .env .env.* *.md requirements-dev.txt
    
    # Install dependencies
    pip install -r requirements.txt -t .
    
    # Create the zip package
    zip -r "$DEPLOYMENT_PACKAGE" . -x "*.pyc" "*/__pycache__/*"
    
    # Move package back to original directory
    mv "$DEPLOYMENT_PACKAGE" "$OLDPWD/"
    cd "$OLDPWD"
    
    # Clean up
    rm -rf "$temp_dir"
    
    log_success "Deployment package created: $DEPLOYMENT_PACKAGE"
}

# Deploy to Lambda
deploy_to_lambda() {
    log_info "Deploying to AWS Lambda..."
    
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    local role_arn="arn:aws:iam::${account_id}:role/${LAMBDA_FUNCTION_NAME}-role"
    
    # Check if function exists
    if aws lambda get-function --function-name "$LAMBDA_FUNCTION_NAME" --region "$AWS_REGION" &> /dev/null; then
        log_info "Updating existing Lambda function..."
        
        aws lambda update-function-code \
            --function-name "$LAMBDA_FUNCTION_NAME" \
            --zip-file "fileb://$DEPLOYMENT_PACKAGE" \
            --region "$AWS_REGION" \
            > /dev/null
        
        log_success "Lambda function updated successfully"
    else
        log_info "Creating new Lambda function..."
        
        aws lambda create-function \
            --function-name "$LAMBDA_FUNCTION_NAME" \
            --runtime python3.12 \
            --role "$role_arn" \
            --handler app.lambda_handler \
            --zip-file "fileb://$DEPLOYMENT_PACKAGE" \
            --timeout 30 \
            --memory-size 512 \
            --region "$AWS_REGION" \
            --environment Variables="{$(cat .env | grep -v '^#' | grep '=' | sed 's/^/"/;s/=/":"/;s/$/",/' | tr -d '\n' | sed 's/,$//')}" \
            > /dev/null
        
        log_success "Lambda function created successfully"
    fi
}

main() {
    echo "============================================================================="
    echo "🚀 Lambda Deployment for Jain Global Trading Bot"
    echo "============================================================================="
    
    create_deployment_package
    deploy_to_lambda
    
    # Clean up
    rm -f "$DEPLOYMENT_PACKAGE"
    
    log_success "🎉 Deployment completed successfully!"
    log_info "Function ARN: arn:aws:lambda:${AWS_REGION}:$(aws sts get-caller-identity --query Account --output text):function:${LAMBDA_FUNCTION_NAME}"
}

main "$@"