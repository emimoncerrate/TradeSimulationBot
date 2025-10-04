#!/bin/bash

# =============================================================================
# Jain Global Slack Trading Bot - Security Configuration Script
# =============================================================================
# This script sets up security configurations, permissions, and compliance
# settings for the Slack Trading Bot.
#
# Usage:
#   ./scripts/setup-slack-security.sh [environment] [region]
#
# Examples:
#   ./scripts/setup-slack-security.sh development us-east-1
#   ./scripts/setup-slack-security.sh production us-west-2
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
# SECURITY POLICY GENERATION
# =============================================================================

log_info "Generating security policies and configurations..."

# Create security configuration directory
mkdir -p config/security

# Generate IAM policy for Slack bot
cat > "config/security/slack-bot-iam-policy.json" << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DynamoDBAccess",
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
                "arn:aws:dynamodb:${AWS_REGION}:*:table/jain-trading-bot-${ENVIRONMENT}-trades",
                "arn:aws:dynamodb:${AWS_REGION}:*:table/jain-trading-bot-${ENVIRONMENT}-positions",
                "arn:aws:dynamodb:${AWS_REGION}:*:table/jain-trading-bot-${ENVIRONMENT}-channels",
                "arn:aws:dynamodb:${AWS_REGION}:*:table/jain-trading-bot-${ENVIRONMENT}-trades/index/*",
                "arn:aws:dynamodb:${AWS_REGION}:*:table/jain-trading-bot-${ENVIRONMENT}-positions/index/*",
                "arn:aws:dynamodb:${AWS_REGION}:*:table/jain-trading-bot-${ENVIRONMENT}-channels/index/*"
            ]
        },
        {
            "Sid": "BedrockAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:${AWS_REGION}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                "arn:aws:bedrock:${AWS_REGION}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
            ]
        },
        {
            "Sid": "CloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams"
            ],
            "Resource": [
                "arn:aws:logs:${AWS_REGION}:*:log-group:/aws/lambda/jain-trading-bot-${ENVIRONMENT}-lambda:*"
            ]
        },
        {
            "Sid": "CloudWatchMetrics",
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricData"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "cloudwatch:namespace": "JainTradingBot/${ENVIRONMENT}"
                }
            }
        },
        {
            "Sid": "XRayTracing",
            "Effect": "Allow",
            "Action": [
                "xray:PutTraceSegments",
                "xray:PutTelemetryRecords"
            ],
            "Resource": "*"
        }
    ]
}
EOF

log_success "IAM policy generated: config/security/slack-bot-iam-policy.json"

# Generate security configuration for different environments
cat > "config/security/security-config-${ENVIRONMENT}.json" << EOF
{
    "environment": "${ENVIRONMENT}",
    "security_level": "$(if [[ "$ENVIRONMENT" == "production" ]]; then echo "high"; else echo "medium"; fi)",
    "encryption": {
        "at_rest": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "true"; else echo "false"; fi),
        "in_transit": true,
        "kms_key_rotation": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "true"; else echo "false"; fi)
    },
    "access_control": {
        "channel_restrictions": true,
        "role_based_access": true,
        "ip_restrictions": false,
        "time_based_restrictions": false
    },
    "audit_logging": {
        "enabled": true,
        "retention_days": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "365"; else echo "30"; fi),
        "log_level": "$(if [[ "$ENVIRONMENT" == "production" ]]; then echo "INFO"; else echo "DEBUG"; fi)",
        "sensitive_data_masking": true
    },
    "rate_limiting": {
        "enabled": true,
        "requests_per_minute": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "100"; else echo "200"; fi),
        "burst_limit": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "200"; else echo "400"; fi)
    },
    "monitoring": {
        "real_time_alerts": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "true"; else echo "false"; fi),
        "security_events": true,
        "performance_monitoring": true,
        "compliance_reporting": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "true"; else echo "false"; fi)
    },
    "compliance": {
        "data_retention": {
            "trades": "7_years",
            "user_activity": "3_years",
            "system_logs": "1_year"
        },
        "data_classification": {
            "trade_data": "confidential",
            "user_data": "restricted",
            "system_data": "internal"
        }
    }
}
EOF

log_success "Security configuration generated: config/security/security-config-${ENVIRONMENT}.json"

# =============================================================================
# CHANNEL SECURITY SETUP
# =============================================================================

log_info "Setting up channel security configurations..."

# Generate approved channels template
cat > "config/security/approved-channels-template.json" << EOF
{
    "environment": "${ENVIRONMENT}",
    "approved_channels": [
        {
            "channel_id": "C1234567890",
            "channel_name": "#trading-${ENVIRONMENT}",
            "description": "Main trading channel for ${ENVIRONMENT}",
            "allowed_roles": ["trader", "analyst", "portfolio_manager"],
            "risk_level": "high",
            "audit_level": "full"
        },
        {
            "channel_id": "C0987654321",
            "channel_name": "#analysis-${ENVIRONMENT}",
            "description": "Research and analysis channel",
            "allowed_roles": ["analyst", "portfolio_manager"],
            "risk_level": "medium",
            "audit_level": "standard"
        },
        {
            "channel_id": "C1122334455",
            "channel_name": "#portfolio-mgmt-${ENVIRONMENT}",
            "description": "Portfolio management channel",
            "allowed_roles": ["portfolio_manager"],
            "risk_level": "high",
            "audit_level": "full"
        }
    ],
    "channel_policies": {
        "require_private": true,
        "require_invitation": true,
        "audit_all_messages": true,
        "restrict_file_uploads": true,
        "require_2fa": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "true"; else echo "false"; fi)
    }
}
EOF

log_success "Channel security template generated: config/security/approved-channels-template.json"

# =============================================================================
# USER ROLE CONFIGURATION
# =============================================================================

log_info "Setting up user role and permission configurations..."

cat > "config/security/user-roles-${ENVIRONMENT}.json" << EOF
{
    "environment": "${ENVIRONMENT}",
    "roles": {
        "research_analyst": {
            "permissions": [
                "view_market_data",
                "create_trade_proposals",
                "view_risk_analysis",
                "access_research_tools"
            ],
            "restrictions": [
                "cannot_execute_trades",
                "cannot_approve_high_risk_trades",
                "limited_portfolio_access"
            ],
            "channels": ["analysis", "research"],
            "risk_limits": {
                "max_trade_value": 100000,
                "max_daily_volume": 500000,
                "requires_approval_above": 50000
            }
        },
        "portfolio_manager": {
            "permissions": [
                "view_all_portfolios",
                "approve_trades",
                "view_comprehensive_risk_analysis",
                "access_management_tools",
                "configure_risk_parameters"
            ],
            "restrictions": [
                "audit_trail_required"
            ],
            "channels": ["trading", "analysis", "portfolio-mgmt"],
            "risk_limits": {
                "max_trade_value": 10000000,
                "max_daily_volume": 50000000,
                "requires_approval_above": 5000000
            }
        },
        "execution_trader": {
            "permissions": [
                "execute_approved_trades",
                "view_execution_status",
                "access_trading_tools",
                "view_position_data"
            ],
            "restrictions": [
                "cannot_modify_trade_parameters",
                "cannot_override_risk_limits",
                "execution_only_access"
            ],
            "channels": ["trading", "execution"],
            "risk_limits": {
                "max_trade_value": 1000000,
                "max_daily_volume": 5000000,
                "requires_approval_above": 500000
            }
        },
        "compliance_officer": {
            "permissions": [
                "view_all_activities",
                "access_audit_logs",
                "configure_compliance_rules",
                "generate_reports"
            ],
            "restrictions": [
                "cannot_execute_trades",
                "read_only_access"
            ],
            "channels": ["all"],
            "risk_limits": {
                "max_trade_value": 0,
                "max_daily_volume": 0,
                "requires_approval_above": 0
            }
        }
    },
    "default_role": "research_analyst",
    "role_assignment": {
        "method": "manual",
        "approval_required": true,
        "audit_changes": true
    }
}
EOF

log_success "User roles configuration generated: config/security/user-roles-${ENVIRONMENT}.json"

# =============================================================================
# SECURITY MONITORING SETUP
# =============================================================================

log_info "Setting up security monitoring configurations..."

cat > "config/security/security-monitoring-${ENVIRONMENT}.json" << EOF
{
    "environment": "${ENVIRONMENT}",
    "monitoring": {
        "security_events": {
            "unauthorized_access_attempts": {
                "enabled": true,
                "threshold": 5,
                "time_window": "5_minutes",
                "action": "alert_and_block"
            },
            "suspicious_trading_patterns": {
                "enabled": true,
                "threshold": 10,
                "time_window": "1_hour",
                "action": "alert_compliance"
            },
            "unusual_channel_activity": {
                "enabled": true,
                "threshold": 100,
                "time_window": "15_minutes",
                "action": "alert_admin"
            },
            "failed_authentication": {
                "enabled": true,
                "threshold": 3,
                "time_window": "5_minutes",
                "action": "temporary_block"
            }
        },
        "compliance_monitoring": {
            "trade_audit_trail": {
                "enabled": true,
                "real_time": true,
                "retention": "7_years"
            },
            "user_activity_logging": {
                "enabled": true,
                "detailed_logging": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "true"; else echo "false"; fi),
                "retention": "3_years"
            },
            "risk_limit_violations": {
                "enabled": true,
                "immediate_alert": true,
                "auto_block": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "true"; else echo "false"; fi)
            }
        },
        "performance_monitoring": {
            "response_time_alerts": {
                "enabled": true,
                "threshold": "5_seconds",
                "action": "alert_ops"
            },
            "error_rate_alerts": {
                "enabled": true,
                "threshold": "5_percent",
                "time_window": "5_minutes",
                "action": "alert_dev_team"
            },
            "resource_utilization": {
                "enabled": true,
                "cpu_threshold": 80,
                "memory_threshold": 85,
                "action": "scale_and_alert"
            }
        }
    },
    "alerting": {
        "channels": {
            "security_alerts": "#security-alerts-${ENVIRONMENT}",
            "compliance_alerts": "#compliance-${ENVIRONMENT}",
            "operational_alerts": "#ops-alerts-${ENVIRONMENT}"
        },
        "escalation": {
            "level_1": "team_lead",
            "level_2": "security_team",
            "level_3": "ciso",
            "timeouts": {
                "level_1": "15_minutes",
                "level_2": "30_minutes",
                "level_3": "60_minutes"
            }
        }
    }
}
EOF

log_success "Security monitoring configuration generated: config/security/security-monitoring-${ENVIRONMENT}.json"

# =============================================================================
# COMPLIANCE CONFIGURATION
# =============================================================================

log_info "Setting up compliance configurations..."

cat > "config/security/compliance-config-${ENVIRONMENT}.json" << EOF
{
    "environment": "${ENVIRONMENT}",
    "compliance_framework": {
        "regulations": [
            "SOX",
            "FINRA",
            "SEC_Rule_15c3-5",
            "GDPR",
            "CCPA"
        ],
        "requirements": {
            "data_retention": {
                "trade_records": "7_years",
                "communication_records": "3_years",
                "audit_logs": "7_years",
                "user_access_logs": "3_years"
            },
            "data_protection": {
                "encryption_at_rest": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "true"; else echo "false"; fi),
                "encryption_in_transit": true,
                "data_masking": true,
                "access_controls": true
            },
            "audit_requirements": {
                "real_time_monitoring": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "true"; else echo "false"; fi),
                "comprehensive_logging": true,
                "tamper_proof_logs": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "true"; else echo "false"; fi),
                "regular_audits": true
            }
        }
    },
    "reporting": {
        "automated_reports": {
            "daily_activity_summary": true,
            "weekly_risk_report": true,
            "monthly_compliance_report": true,
            "quarterly_audit_report": $(if [[ "$ENVIRONMENT" == "production" ]]; then echo "true"; else echo "false"; fi)
        },
        "alert_reports": {
            "security_incidents": true,
            "compliance_violations": true,
            "risk_limit_breaches": true,
            "system_anomalies": true
        }
    },
    "data_governance": {
        "data_classification": {
            "public": [],
            "internal": ["system_logs", "performance_metrics"],
            "confidential": ["trade_data", "user_profiles"],
            "restricted": ["authentication_tokens", "api_keys"]
        },
        "access_matrix": {
            "public": ["all_users"],
            "internal": ["employees"],
            "confidential": ["authorized_users"],
            "restricted": ["system_administrators"]
        },
        "retention_policies": {
            "automatic_deletion": true,
            "legal_hold_support": true,
            "backup_retention": "$(if [[ "$ENVIRONMENT" == "production" ]]; then echo "10_years"; else echo "1_year"; fi)"
        }
    }
}
EOF

log_success "Compliance configuration generated: config/security/compliance-config-${ENVIRONMENT}.json"

# =============================================================================
# SECURITY VALIDATION SCRIPT
# =============================================================================

cat > "scripts/validate-security-config.sh" << 'EOF'
#!/bin/bash

# Security Configuration Validation Script

set -e

ENVIRONMENT=${1:-development}
AWS_REGION=${2:-us-east-1}

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

PASSED=0
FAILED=0
WARNINGS=0

validate_security_configs() {
    log_info "Validating security configuration files..."
    
    CONFIG_FILES=(
        "config/security/slack-bot-iam-policy.json"
        "config/security/security-config-${ENVIRONMENT}.json"
        "config/security/approved-channels-template.json"
        "config/security/user-roles-${ENVIRONMENT}.json"
        "config/security/security-monitoring-${ENVIRONMENT}.json"
        "config/security/compliance-config-${ENVIRONMENT}.json"
    )
    
    for file in "${CONFIG_FILES[@]}"; do
        if [[ -f "$file" ]]; then
            if jq empty "$file" 2>/dev/null; then
                log_success "Valid configuration file: $file"
                ((PASSED++))
            else
                log_error "Invalid JSON in configuration file: $file"
                ((FAILED++))
            fi
        else
            log_error "Missing configuration file: $file"
            ((FAILED++))
        fi
    done
}

validate_iam_permissions() {
    log_info "Validating IAM permissions..."
    
    FUNCTION_NAME="jain-trading-bot-${ENVIRONMENT}-lambda"
    
    if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" &> /dev/null; then
        ROLE_ARN=$(aws lambda get-function \
            --function-name "$FUNCTION_NAME" \
            --region "$AWS_REGION" \
            --query 'Configuration.Role' \
            --output text)
        
        if [[ -n "$ROLE_ARN" ]]; then
            log_success "Lambda execution role found: $ROLE_ARN"
            ((PASSED++))
        else
            log_error "Lambda execution role not found"
            ((FAILED++))
        fi
    else
        log_warning "Lambda function not found (may not be deployed yet)"
        ((WARNINGS++))
    fi
}

validate_encryption() {
    log_info "Validating encryption settings..."
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        # Check for KMS key
        if aws cloudformation describe-stacks \
           --stack-name "jain-trading-bot-${ENVIRONMENT}" \
           --region "$AWS_REGION" \
           --query 'Stacks[0].Outputs[?OutputKey==`KMSKeyId`].OutputValue' \
           --output text 2>/dev/null | grep -q .; then
            log_success "KMS key configured for production"
            ((PASSED++))
        else
            log_warning "KMS key not found for production environment"
            ((WARNINGS++))
        fi
    else
        log_info "Encryption validation skipped for non-production environment"
    fi
}

validate_monitoring() {
    log_info "Validating security monitoring setup..."
    
    # Check for CloudWatch alarms
    ALARM_COUNT=$(aws cloudwatch describe-alarms \
        --alarm-name-prefix "JainTradingBot-${ENVIRONMENT}" \
        --region "$AWS_REGION" \
        --query 'length(MetricAlarms)' \
        --output text 2>/dev/null || echo "0")
    
    if [[ "$ALARM_COUNT" -gt 0 ]]; then
        log_success "Security monitoring alarms configured: $ALARM_COUNT alarms"
        ((PASSED++))
    else
        log_warning "No security monitoring alarms found"
        ((WARNINGS++))
    fi
}

# Run validations
log_info "Starting security configuration validation for $ENVIRONMENT environment"
echo

validate_security_configs
validate_iam_permissions
validate_encryption
validate_monitoring

# Summary
echo
log_info "=== SECURITY VALIDATION SUMMARY ==="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo

if [[ $FAILED -eq 0 ]]; then
    log_success "Security configuration validation completed successfully!"
    exit 0
else
    log_error "Security configuration validation failed with $FAILED errors"
    exit 1
fi
EOF

chmod +x scripts/validate-security-config.sh
log_success "Security validation script created: scripts/validate-security-config.sh"

# =============================================================================
# SUMMARY
# =============================================================================

echo
log_success "=== SECURITY CONFIGURATION COMPLETED ==="
echo
log_info "Generated Security Files:"
log_info "  - config/security/slack-bot-iam-policy.json"
log_info "  - config/security/security-config-${ENVIRONMENT}.json"
log_info "  - config/security/approved-channels-template.json"
log_info "  - config/security/user-roles-${ENVIRONMENT}.json"
log_info "  - config/security/security-monitoring-${ENVIRONMENT}.json"
log_info "  - config/security/compliance-config-${ENVIRONMENT}.json"
log_info "  - scripts/validate-security-config.sh"
echo
log_info "Security Features Configured:"
log_info "  - IAM policies with least privilege access"
log_info "  - Role-based access control"
log_info "  - Channel restrictions and validation"
log_info "  - Comprehensive audit logging"
log_info "  - Security monitoring and alerting"
log_info "  - Compliance reporting and data governance"
echo
log_warning "Next Steps:"
log_warning "1. Review and customize the security configurations"
log_warning "2. Update approved channels list with actual channel IDs"
log_warning "3. Configure user roles and permissions"
log_warning "4. Set up security monitoring alerts"
log_warning "5. Run security validation: ./scripts/validate-security-config.sh ${ENVIRONMENT} ${AWS_REGION}"
echo
log_success "Security configuration completed at $(date)"