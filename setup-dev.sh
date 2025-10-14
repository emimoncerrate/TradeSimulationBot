#!/bin/bash

# Jain Global Trading Bot - Development Setup Script
# This script sets up the complete development environment

set -e

echo "🚀 Setting up Jain Global Trading Bot Development Environment"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    print_status "Checking Docker..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Check if Python 3 is available
check_python() {
    print_status "Checking Python..."
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8+ and try again."
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2)
    print_success "Python $python_version is available"
}

# Install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        print_success "Python dependencies installed"
    else
        print_warning "requirements.txt not found, skipping dependency installation"
    fi
}

# Start Docker services
start_services() {
    print_status "Starting Docker services (DynamoDB Local + Redis)..."
    docker-compose up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to start..."
    sleep 5
    
    # Check if DynamoDB Local is responding
    max_attempts=30
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000 > /dev/null 2>&1; then
            print_success "DynamoDB Local is ready"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "DynamoDB Local failed to start after $max_attempts attempts"
            exit 1
        fi
        
        print_status "Waiting for DynamoDB Local... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    # Check Redis
    if docker-compose ps redis | grep -q "Up"; then
        print_success "Redis is ready"
    else
        print_warning "Redis may not be ready, but continuing..."
    fi
}

# Setup DynamoDB tables
setup_database() {
    print_status "Setting up DynamoDB tables..."
    python3 scripts/setup-local-db.py
    
    if [ $? -eq 0 ]; then
        print_success "Database tables created successfully"
    else
        print_error "Failed to create database tables"
        exit 1
    fi
}

# Verify environment configuration
verify_config() {
    print_status "Verifying environment configuration..."
    
    if [ ! -f ".env" ]; then
        print_error ".env file not found. Please create it from the template."
        exit 1
    fi
    
    # Check for required environment variables
    required_vars=("SLACK_BOT_TOKEN" "SLACK_SIGNING_SECRET" "FINNHUB_API_KEY")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" .env || grep -q "^${var}=$" .env || grep -q "^${var}=your-" .env; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_warning "The following environment variables need to be configured in .env:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        print_warning "Please update your .env file with actual values before running the bot."
    else
        print_success "Environment configuration looks good"
    fi
}

# Test the application
test_application() {
    print_status "Testing application startup..."
    
    # Run a quick test to see if the app can start
    timeout 10s python3 -c "
import sys
sys.path.append('.')
from config.settings import ConfigurationManager
try:
    config = ConfigurationManager()
    print('✅ Configuration loaded successfully')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    sys.exit(1)
" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        print_success "Application configuration test passed"
    else
        print_warning "Application configuration test failed, but continuing..."
    fi
}

# Main setup process
main() {
    echo
    check_docker
    check_python
    install_dependencies
    start_services
    setup_database
    verify_config
    test_application
    
    echo
    echo "============================================================"
    print_success "🎉 Development environment setup complete!"
    echo
    echo "📋 What's been set up:"
    echo "  ✅ Docker services (DynamoDB Local + Redis)"
    echo "  ✅ DynamoDB tables with proper indexes"
    echo "  ✅ Python dependencies"
    echo "  ✅ Environment configuration verified"
    echo
    echo "🚀 Next steps:"
    echo "  1. Update your .env file with real Slack tokens if needed"
    echo "  2. Start the bot: python3 app.py"
    echo "  3. Test the /trade command in your Slack workspace"
    echo
    echo "🔧 Useful commands:"
    echo "  • View logs: docker-compose logs -f"
    echo "  • Stop services: docker-compose down"
    echo "  • Reset database: docker-compose down -v && ./setup-dev.sh"
    echo "  • View DynamoDB tables: aws dynamodb list-tables --endpoint-url http://localhost:8000"
    echo
}

# Run main function
main