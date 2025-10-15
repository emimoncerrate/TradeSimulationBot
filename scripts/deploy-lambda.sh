#!/bin/bash

# =============================================================================
# Jain Global Slack Trading Bot - AWS Lambda Deployment Script
# =============================================================================
# This script handles deployment of the Slack Trading Bot to AWS Lambda
# using AWS SAM (Serverless Application Model) with support for different
# environments and deployment strategies.

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEFAULT_ENVIRONMENT="development"
DEFAULT_REGION="us-east-1"

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

# Help function
show_help() {
    cat << EOF
AWS Lambda Deployment Script for Jain Global Slack Trading Bot

Usage: $0 [OPTIONS] COMMAND

COMMANDS:
    build           Build SAM application
    deploy          Deploy to AWS Lambda
    package         Package application for deployment
    validate        Validate SAM template
    delete          Delete CloudFormation stack
    logs            Tail Lambda function logs
    invoke          Invoke Lambda function for testing

OPTIONS:
    -e, --environment ENV   Deployment environment (default: development)
    -r, --region REGION     AWS region (default: us-east-1)
    -s, --stack-name NAME   CloudFormation stack name
    -b, --s3-bucket BUCKET  S3 bucket for deployment artifacts
    -p, --profile PROFILE   AWS CLI profile to use
    --guided                Use guided deployment (interactive)
    --confirm-changeset     Confirm changeset before deployment
    --capabilities CAPS     CloudFormation capabilities (comma-separated)
    --parameter-overrides   Parameter overrides (KEY=VALUE format)
    -v, --verbose           Verbose output
    -h, --help              Show this help message

EXAMPLES:
    $0 build --environment production
    $0 deploy --environment staging --guided
    $0 package --s3-bucket my-deployment-bucket
    $0 logs --environment production --tail
    $0 invoke --environment development --event test-event.json

ENVIRONMENT VARIABLES:
    AWS_PROFILE             Default AWS CLI profile
    AWS_REGION              Default AWS region
    SAM_CLI_TELEMETRY       Disable SAM CLI telemetry (set to 0)
    SLACK_BOT_TOKEN         Slack bot token (required for deployment)
    SLACK_SIGNING_SECRET    Slack signing secret (required for deployment)
    FINNHUB_API_KEY         Finnhub API key (required for deployment)

EOF
}

# Parse command line arguments
COMMAND=""
ENVIRONMENT="$DEFAULT_ENVIRONMENT"
REGION="$DEFAULT_REGION"
STACK_NAME=""
S3_BUCKET=""
PROFILE="${AWS_PROFILE:-}"
GUIDED=false
CONFIRM_CHANGESET=false
CAPABILITIES=""
PARAMETER_OVERRIDES=()
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -s|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        -b|--s3-bucket)
            S3_BUCKET="$2"
            shift 2
            ;;
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        --guided)
            GUIDED=true
            shift
            ;;
        --confirm-changeset)
            CONFIRM_CHANGESET=true
            shift
            ;;
        --capabilities)
            CAPABILITIES="$2"
            shift 2
            ;;
        --parameter-overrides)
            IFS=',' read -ra OVERRIDES <<< "$2"
            for override in "${OVERRIDES[@]}"; do
                PARAMETER_OVERRIDES+=("$override")
            done
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            if [[ -z "$COMMAND" ]]; then
                COMMAND="$1"
            else
                log_error "Multiple commands specified: $COMMAND and $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate command
if [[ -z "$COMMAND" ]]; then
    log_error "No command specified"
    show_help
    exit 1
fi

if [[ ! "$COMMAND" =~ ^(build|deploy|package|validate|delete|logs|invoke)$ ]]; then
    log_error "Invalid command: $COMMAND"
    show_help
    exit 1
fi

# Set default stack name if not provided
if [[ -z "$STACK_NAME" ]]; then
    STACK_NAME="jain-trading-bot-${ENVIRONMENT}"
fi

# Change to project root
cd "$PROJECT_ROOT"

# Validate dependencies
validate_dependencies() {
    local missing_deps=()
    
    # Check for SAM CLI
    if ! command -v sam &> /dev/null; then
        missing_deps+=("sam")
    fi
    
    # Check for AWS CLI
    if ! command -v aws &> /dev/null; then
        missing_deps+=("aws")
    fi
    
    # Check for Docker (required for SAM build)
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_info "Please install the missing dependencies and try again."
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
}

# Validate AWS credentials
validate_aws_credentials() {
    log_info "Validating AWS credentials..."
    
    local aws_cmd=(aws sts get-caller-identity)
    
    if [[ -n "$PROFILE" ]]; then
        aws_cmd+=(--profile "$PROFILE")
    fi
    
    if [[ -n "$REGION" ]]; then
        aws_cmd+=(--region "$REGION")
    fi
    
    if "${aws_cmd[@]}" &> /dev/null; then
        local account_id
        account_id=$("${aws_cmd[@]}" --query Account --output text)
        log_success "AWS credentials validated. Account ID: $account_id"
    else
        log_error "AWS credentials validation failed"
        exit 1
    fi
}

# Validate environment variables
validate_environment_variables() {
    local required_vars=()
    
    if [[ "$COMMAND" == "deploy" ]]; then
        if [[ -z "${SLACK_BOT_TOKEN:-}" ]]; then
            required_vars+=("SLACK_BOT_TOKEN")
        fi
        
        if [[ -z "${SLACK_SIGNING_SECRET:-}" ]]; then
            required_vars+=("SLACK_SIGNING_SECRET")
        fi
        
        if [[ -z "${FINNHUB_API_KEY:-}" ]]; then
            required_vars+=("FINNHUB_API_KEY")
        fi
    fi
    
    if [[ ${#required_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables: ${required_vars[*]}"
        log_info "Please set these variables and try again."
        exit 1
    fi
}

# Build SAM application
sam_build() {
    log_info "Building SAM application..."
    
    local build_cmd=(sam build)
    
    if [[ "$VERBOSE" == true ]]; then
        build_cmd+=(--debug)
    fi
    
    # Use container-based builds for consistency
    build_cmd+=(--use-container)
    
    if "${build_cmd[@]}"; then
        log_success "SAM build completed successfully"
    else
        log_error "SAM build failed"
        exit 1
    fi
}

# Package SAM application
sam_package() {
    log_info "Packaging SAM application..."
    
    if [[ -z "$S3_BUCKET" ]]; then
        log_error "S3 bucket is required for packaging"
        exit 1
    fi
    
    local package_cmd=(sam package)
    package_cmd+=(--s3-bucket "$S3_BUCKET")
    package_cmd+=(--output-template-file packaged-template.yaml)
    
    if [[ -n "$PROFILE" ]]; then
        package_cmd+=(--profile "$PROFILE")
    fi
    
    if [[ -n "$REGION" ]]; then
        package_cmd+=(--region "$REGION")
    fi
    
    if "${package_cmd[@]}"; then
        log_success "SAM package completed successfully"
    else
        log_error "SAM package failed"
        exit 1
    fi
}

# Deploy SAM application
sam_deploy() {
    log_info "Deploying SAM application to $ENVIRONMENT environment..."
    
    local deploy_cmd=(sam deploy)
    
    # Add stack name
    deploy_cmd+=(--stack-name "$STACK_NAME")
    
    # Add region
    if [[ -n "$REGION" ]]; then
        deploy_cmd+=(--region "$REGION")
    fi
    
    # Add profile
    if [[ -n "$PROFILE" ]]; then
        deploy_cmd+=(--profile "$PROFILE")
    fi
    
    # Add capabilities
    if [[ -n "$CAPABILITIES" ]]; then
        deploy_cmd+=(--capabilities "$CAPABILITIES")
    else
        deploy_cmd+=(--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM)
    fi
    
    # Add parameter overrides
    if [[ ${#PARAMETER_OVERRIDES[@]} -gt 0 ]]; then
        local param_string=""
        for param in "${PARAMETER_OVERRIDES[@]}"; do
            if [[ -n "$param_string" ]]; then
                param_string="$param_string $param"
            else
                param_string="$param"
            fi
        done
        deploy_cmd+=(--parameter-overrides "$param_string")
    fi
    
    # Add environment-specific parameters
    deploy_cmd+=(--parameter-overrides)
    deploy_cmd+=("Environment=$ENVIRONMENT")
    deploy_cmd+=("SlackBotToken=$SLACK_BOT_TOKEN")
    deploy_cmd+=("SlackSigningSecret=$SLACK_SIGNING_SECRET")
    deploy_cmd+=("FinnhubApiKey=$FINNHUB_API_KEY")
    
    # Add S3 bucket if provided
    if [[ -n "$S3_BUCKET" ]]; then
        deploy_cmd+=(--s3-bucket "$S3_BUCKET")
    fi
    
    # Add guided deployment
    if [[ "$GUIDED" == true ]]; then
        deploy_cmd+=(--guided)
    fi
    
    # Add confirm changeset
    if [[ "$CONFIRM_CHANGESET" == true ]]; then
        deploy_cmd+=(--confirm-changeset)
    fi
    
    # Add verbose output
    if [[ "$VERBOSE" == true ]]; then
        deploy_cmd+=(--debug)
    fi
    
    if "${deploy_cmd[@]}"; then
        log_success "SAM deployment completed successfully"
        
        # Get stack outputs
        log_info "Retrieving stack outputs..."
        get_stack_outputs
    else
        log_error "SAM deployment failed"
        exit 1
    fi
}

# Get CloudFormation stack outputs
get_stack_outputs() {
    local describe_cmd=(aws cloudformation describe-stacks)
    describe_cmd+=(--stack-name "$STACK_NAME")
    
    if [[ -n "$PROFILE" ]]; then
        describe_cmd+=(--profile "$PROFILE")
    fi
    
    if [[ -n "$REGION" ]]; then
        describe_cmd+=(--region "$REGION")
    fi
    
    local outputs
    outputs=$("${describe_cmd[@]}" --query 'Stacks[0].Outputs' --output table 2>/dev/null || echo "[]")
    
    if [[ "$outputs" != "[]" ]]; then
        log_info "Stack outputs:"
        echo "$outputs"
    fi
}

# Validate SAM template
sam_validate() {
    log_info "Validating SAM template..."
    
    local validate_cmd=(sam validate)
    
    if [[ "$VERBOSE" == true ]]; then
        validate_cmd+=(--debug)
    fi
    
    if "${validate_cmd[@]}"; then
        log_success "SAM template validation passed"
    else
        log_error "SAM template validation failed"
        exit 1
    fi
}

# Delete CloudFormation stack
sam_delete() {
    log_warning "This will delete the entire CloudFormation stack: $STACK_NAME"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deletion cancelled"
        exit 0
    fi
    
    log_info "Deleting CloudFormation stack: $STACK_NAME"
    
    local delete_cmd=(aws cloudformation delete-stack)
    delete_cmd+=(--stack-name "$STACK_NAME")
    
    if [[ -n "$PROFILE" ]]; then
        delete_cmd+=(--profile "$PROFILE")
    fi
    
    if [[ -n "$REGION" ]]; then
        delete_cmd+=(--region "$REGION")
    fi
    
    if "${delete_cmd[@]}"; then
        log_success "Stack deletion initiated. Monitor progress in AWS Console."
    else
        log_error "Stack deletion failed"
        exit 1
    fi
}

# Tail Lambda function logs
sam_logs() {
    log_info "Tailing Lambda function logs..."
    
    local logs_cmd=(sam logs)
    logs_cmd+=(--stack-name "$STACK_NAME")
    logs_cmd+=(--tail)
    
    if [[ -n "$PROFILE" ]]; then
        logs_cmd+=(--profile "$PROFILE")
    fi
    
    if [[ -n "$REGION" ]]; then
        logs_cmd+=(--region "$REGION")
    fi
    
    "${logs_cmd[@]}"
}

# Invoke Lambda function
sam_invoke() {
    log_info "Invoking Lambda function..."
    
    local invoke_cmd=(sam local invoke)
    
    # Add event file if it exists
    if [[ -f "events/test-event.json" ]]; then
        invoke_cmd+=(--event events/test-event.json)
    fi
    
    if [[ "$VERBOSE" == true ]]; then
        invoke_cmd+=(--debug)
    fi
    
    "${invoke_cmd[@]}"
}

# Main execution
main() {
    log_info "Starting AWS Lambda deployment process..."
    log_info "Command: $COMMAND"
    log_info "Environment: $ENVIRONMENT"
    log_info "Region: $REGION"
    log_info "Stack Name: $STACK_NAME"
    
    # Validate dependencies
    validate_dependencies
    
    # Validate AWS credentials
    validate_aws_credentials
    
    # Validate environment variables
    validate_environment_variables
    
    # Execute command
    case "$COMMAND" in
        build)
            sam_build
            ;;
        deploy)
            sam_build
            sam_deploy
            ;;
        package)
            sam_build
            sam_package
            ;;
        validate)
            sam_validate
            ;;
        delete)
            sam_delete
            ;;
        logs)
            sam_logs
            ;;
        invoke)
            sam_invoke
            ;;
    esac
    
    log_success "AWS Lambda deployment process completed successfully!"
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Deployment process failed with exit code $exit_code"
    fi
    exit $exit_code
}

# Set up cleanup trap
trap cleanup EXIT

# Disable SAM CLI telemetry
export SAM_CLI_TELEMETRY=0

# Run main function
main