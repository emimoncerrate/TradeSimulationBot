#!/bin/bash

# =============================================================================
# Jain Global Slack Trading Bot - Docker Build Script
# =============================================================================
# This script builds Docker images for different deployment targets:
# - development: Local development with hot reload
# - production: Optimized production deployment
# - lambda: AWS Lambda container deployment
# - testing: CI/CD testing environment

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGE_NAME="jain-global/slack-trading-bot"
DEFAULT_TAG="latest"

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
Docker Build Script for Jain Global Slack Trading Bot

Usage: $0 [OPTIONS] TARGET

TARGETS:
    development     Build development image with hot reload
    production      Build optimized production image
    lambda          Build AWS Lambda container image
    testing         Build testing image for CI/CD
    all             Build all targets

OPTIONS:
    -t, --tag TAG           Docker image tag (default: latest)
    -r, --registry URL      Docker registry URL for pushing
    -p, --push              Push images to registry after building
    -c, --clean             Clean build (no cache)
    --platform PLATFORM    Target platform (e.g., linux/amd64,linux/arm64)
    --build-arg ARG=VALUE   Pass build argument to Docker
    -v, --verbose           Verbose output
    -h, --help              Show this help message

EXAMPLES:
    $0 development
    $0 production --tag v1.0.0 --push
    $0 lambda --registry 123456789012.dkr.ecr.us-east-1.amazonaws.com
    $0 all --clean --verbose

ENVIRONMENT VARIABLES:
    DOCKER_REGISTRY         Default registry URL
    DOCKER_BUILDKIT         Enable BuildKit (default: 1)
    AWS_ACCOUNT_ID          AWS account ID for ECR
    AWS_REGION              AWS region for ECR (default: us-east-1)

EOF
}

# Parse command line arguments
TARGET=""
TAG="$DEFAULT_TAG"
REGISTRY="${DOCKER_REGISTRY:-}"
PUSH=false
CLEAN=false
PLATFORM=""
VERBOSE=false
BUILD_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --build-arg)
            BUILD_ARGS+=("--build-arg" "$2")
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
            if [[ -z "$TARGET" ]]; then
                TARGET="$1"
            else
                log_error "Multiple targets specified: $TARGET and $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate target
if [[ -z "$TARGET" ]]; then
    log_error "No target specified"
    show_help
    exit 1
fi

if [[ ! "$TARGET" =~ ^(development|production|lambda|testing|all)$ ]]; then
    log_error "Invalid target: $TARGET"
    show_help
    exit 1
fi

# Enable BuildKit for better performance
export DOCKER_BUILDKIT=1

# Change to project root
cd "$PROJECT_ROOT"

# Validate Docker is available
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    log_error "Docker daemon is not running"
    exit 1
fi

# Build function
build_image() {
    local target=$1
    local image_tag="${IMAGE_NAME}:${target}-${TAG}"
    
    if [[ -n "$REGISTRY" ]]; then
        image_tag="${REGISTRY}/${image_tag}"
    fi
    
    log_info "Building $target image: $image_tag"
    
    # Prepare build command
    local build_cmd=(docker build)
    
    # Add build arguments
    build_cmd+=("${BUILD_ARGS[@]}")
    
    # Add platform if specified
    if [[ -n "$PLATFORM" ]]; then
        build_cmd+=(--platform "$PLATFORM")
    fi
    
    # Add clean flag if specified
    if [[ "$CLEAN" == true ]]; then
        build_cmd+=(--no-cache)
    fi
    
    # Add target and tag
    build_cmd+=(--target "$target" --tag "$image_tag")
    
    # Add context
    build_cmd+=(.)
    
    # Execute build command
    if [[ "$VERBOSE" == true ]]; then
        log_info "Executing: ${build_cmd[*]}"
    fi
    
    if "${build_cmd[@]}"; then
        log_success "Successfully built $target image: $image_tag"
        
        # Push if requested
        if [[ "$PUSH" == true && -n "$REGISTRY" ]]; then
            log_info "Pushing $target image to registry..."
            if docker push "$image_tag"; then
                log_success "Successfully pushed $target image: $image_tag"
            else
                log_error "Failed to push $target image: $image_tag"
                return 1
            fi
        fi
        
        return 0
    else
        log_error "Failed to build $target image"
        return 1
    fi
}

# Setup AWS ECR if using AWS registry
setup_ecr() {
    if [[ "$REGISTRY" =~ \.amazonaws\.com ]]; then
        log_info "Detected AWS ECR registry, setting up authentication..."
        
        local aws_region="${AWS_REGION:-us-east-1}"
        local aws_account_id="${AWS_ACCOUNT_ID:-}"
        
        if [[ -z "$aws_account_id" ]]; then
            # Try to extract account ID from registry URL
            if [[ "$REGISTRY" =~ ^([0-9]+)\.dkr\.ecr\. ]]; then
                aws_account_id="${BASH_REMATCH[1]}"
            else
                log_error "Cannot determine AWS account ID. Set AWS_ACCOUNT_ID environment variable."
                return 1
            fi
        fi
        
        # Login to ECR
        if command -v aws &> /dev/null; then
            log_info "Logging in to ECR..."
            if aws ecr get-login-password --region "$aws_region" | docker login --username AWS --password-stdin "$REGISTRY"; then
                log_success "Successfully logged in to ECR"
            else
                log_error "Failed to login to ECR"
                return 1
            fi
        else
            log_warning "AWS CLI not found. Make sure you're authenticated to ECR."
        fi
        
        # Create repository if it doesn't exist
        local repo_name="${IMAGE_NAME}"
        if aws ecr describe-repositories --repository-names "$repo_name" --region "$aws_region" &> /dev/null; then
            log_info "ECR repository $repo_name already exists"
        else
            log_info "Creating ECR repository: $repo_name"
            if aws ecr create-repository --repository-name "$repo_name" --region "$aws_region" &> /dev/null; then
                log_success "Successfully created ECR repository: $repo_name"
            else
                log_error "Failed to create ECR repository: $repo_name"
                return 1
            fi
        fi
    fi
}

# Main execution
main() {
    log_info "Starting Docker build process..."
    log_info "Target: $TARGET"
    log_info "Tag: $TAG"
    log_info "Registry: ${REGISTRY:-"(none)"}"
    log_info "Push: $PUSH"
    log_info "Clean: $CLEAN"
    
    # Setup ECR if needed
    if [[ "$PUSH" == true && -n "$REGISTRY" ]]; then
        setup_ecr
    fi
    
    # Build images based on target
    case "$TARGET" in
        development|production|lambda|testing)
            build_image "$TARGET"
            ;;
        all)
            log_info "Building all targets..."
            local targets=(development production lambda testing)
            local failed_targets=()
            
            for target in "${targets[@]}"; do
                if ! build_image "$target"; then
                    failed_targets+=("$target")
                fi
            done
            
            if [[ ${#failed_targets[@]} -eq 0 ]]; then
                log_success "Successfully built all targets"
            else
                log_error "Failed to build targets: ${failed_targets[*]}"
                exit 1
            fi
            ;;
    esac
    
    log_success "Docker build process completed successfully!"
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Build process failed with exit code $exit_code"
    fi
    exit $exit_code
}

# Set up cleanup trap
trap cleanup EXIT

# Run main function
main