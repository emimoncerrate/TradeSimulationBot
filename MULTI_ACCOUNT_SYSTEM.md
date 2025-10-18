# Multi-Account Alpaca Trading System

This document describes the multi-account Alpaca trading system that allows multiple users to trade with isolated accounts, providing better scalability and user management.

## 🏗️ System Architecture

### Core Components

1. **MultiAlpacaService** (`services/multi_alpaca_service.py`)
   - Manages multiple Alpaca trading accounts
   - Handles account initialization and health monitoring
   - Provides account-specific trading operations
   - Supports load balancing across accounts

2. **UserAccountManager** (`services/user_account_manager.py`)
   - Manages user-to-account assignments
   - Supports multiple assignment strategies
   - Tracks assignment history and statistics
   - Handles automatic user assignment

3. **MultiAccountTradeCommand** (`listeners/multi_account_trade_command.py`)
   - Enhanced trade command with multi-account support
   - Automatic account assignment for new users
   - Account-specific trade execution
   - Account balance validation

4. **AccountManagementCommands** (`commands/account_management.py`)
   - Slack commands for account management
   - User assignment and reassignment
   - Account status monitoring
   - User-to-account mapping

## 🔧 Configuration

### Environment Variables

The system supports multiple Alpaca accounts through environment variables:

```bash
# Primary Account (existing configuration)
ALPACA_PAPER_API_KEY=PKBP0EO6JAUDARK9BAJK
ALPACA_PAPER_SECRET_KEY=KIhKDwfNmtYY6I0lJ5IjAmJUyrVnQcDVjmfscvcD
ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets
ALPACA_PAPER_ENABLED=true
ALPACA_STARTING_CASH=100000.00

# Additional Accounts
ALPACA_PAPER_API_KEY_1=PK_YOUR_SECOND_API_KEY_HERE
ALPACA_PAPER_SECRET_KEY_1=YOUR_SECOND_SECRET_KEY_HERE
ALPACA_PAPER_BASE_URL_1=https://paper-api.alpaca.markets

ALPACA_PAPER_API_KEY_2=PK_YOUR_THIRD_API_KEY_HERE
ALPACA_PAPER_SECRET_KEY_2=YOUR_THIRD_SECRET_KEY_HERE
ALPACA_PAPER_BASE_URL_2=https://paper-api.alpaca.markets

# Add more accounts as needed...
```

### Account Setup

1. **Create Multiple Alpaca Paper Trading Accounts**
   - Visit [Alpaca Markets](https://alpaca.markets/)
   - Create separate paper trading accounts for each user group
   - Generate API keys for each account (ensure they start with 'PK')

2. **Configure Environment Variables**
   - Add the API keys to your `.env` file
   - Use the naming convention shown above
   - Ensure all keys are paper trading keys for safety

3. **Verify Configuration**
   - Run the test script: `python test_multi_account_system.py`
   - Check that all accounts are properly initialized

## 🚀 Features

### User Assignment Strategies

The system supports multiple user assignment strategies:

1. **Least Loaded** (default)
   - Assigns users to the account with the fewest users
   - Provides automatic load balancing

2. **Round Robin**
   - Distributes users evenly across all accounts
   - Simple rotation-based assignment

3. **Department Based**
   - Assigns users based on their department
   - Customizable department-to-account mapping

4. **Manual**
   - Requires explicit admin assignment
   - Full control over user placement

### Slack Commands

#### Trading Commands

- `/trade` - Enhanced trade command with account selection
- `/trade AAPL` - Quick trade with symbol pre-filled

#### Account Management Commands

- `/accounts` - Show all available accounts and their status
- `/assign-account @user account_id` - Assign a user to a specific account
- `/my-account` - Show current user's account assignment
- `/account-users` - Show users assigned to each account

### Account Isolation

Each user is assigned to a specific Alpaca account, providing:

- **Portfolio Isolation**: Each user's trades are isolated to their assigned account
- **Balance Separation**: Users can only trade with their account's available funds
- **Performance Tracking**: Individual account performance can be monitored
- **Risk Management**: Account-level risk controls and limits

## 🔄 User Flow

### New User Registration

1. User runs `/trade` command for the first time
2. System checks if user has an assigned account
3. If not assigned, system auto-assigns based on strategy
4. User sees their account information in the trade modal
5. All subsequent trades execute on their assigned account

### Existing User Trading

1. User runs `/trade` command
2. System retrieves user's assigned account
3. Trade modal shows account-specific information
4. Trade executes on user's assigned account
5. User receives confirmation with updated account balance

### Account Management

1. Admins can view all accounts with `/accounts`
2. Admins can manually assign users with `/assign-account`
3. Users can check their account with `/my-account`
4. Admins can view user distribution with `/account-users`

## 📊 Monitoring and Analytics

### Account Status Monitoring

The system continuously monitors:

- Account connectivity and health
- Available cash and buying power
- Portfolio values and performance
- User assignment distribution
- Trade execution success rates

### Assignment Statistics

Track user assignment patterns:

- Total users per account
- Assignment strategy effectiveness
- Load balancing metrics
- Account utilization rates

## 🔒 Security Features

### Paper Trading Enforcement

- All API keys must start with 'PK' (paper trading)
- System validates keys during initialization
- Prevents accidental live trading

### Access Control

- User authentication required for all operations
- Role-based permissions for account management
- Audit trail for all assignments and trades

### Error Handling

- Graceful fallback to single-account mode
- Comprehensive error logging and reporting
- User-friendly error messages

## 🧪 Testing

### Test Script

Run the comprehensive test script:

```bash
python test_multi_account_system.py
```

This tests:
- Service container integration
- Multi-account service initialization
- User assignment functionality
- Account information retrieval
- Command integration

### Manual Testing

1. **Test Account Assignment**
   ```
   /my-account
   ```

2. **Test Account Management**
   ```
   /accounts
   /assign-account @testuser primary
   /account-users
   ```

3. **Test Trading**
   ```
   /trade AAPL
   ```

## 🚨 Troubleshooting

### Common Issues

1. **No Accounts Available**
   - Check environment variable configuration
   - Verify API keys are valid and paper trading
   - Check network connectivity to Alpaca

2. **User Assignment Fails**
   - Ensure at least one account is active
   - Check assignment strategy configuration
   - Verify database connectivity

3. **Trade Execution Fails**
   - Check account has sufficient buying power
   - Verify market hours and symbol validity
   - Check Alpaca API status

### Debug Mode

Enable debug logging by setting:

```bash
export LOG_LEVEL=DEBUG
```

### Fallback Behavior

If the multi-account system fails to initialize:
- System automatically falls back to single-account mode
- Original trade command functionality is preserved
- Users receive notification about limited functionality

## 📈 Scaling Considerations

### Adding More Accounts

1. Create new Alpaca paper trading accounts
2. Add environment variables with incremental numbers
3. Restart the application
4. System automatically detects and initializes new accounts

### Performance Optimization

- Account status is cached and updated periodically
- User assignments are stored in memory for fast lookup
- Database persistence for assignment history

### Load Balancing

- Monitor account utilization with `/accounts`
- Adjust assignment strategy based on usage patterns
- Consider manual reassignment for heavy users

## 🔮 Future Enhancements

### Planned Features

1. **Dynamic Account Scaling**
   - Automatic account provisioning based on load
   - Integration with Alpaca account creation API

2. **Advanced Analytics**
   - Account performance dashboards
   - User trading pattern analysis
   - Risk metrics and alerts

3. **Enhanced Assignment Strategies**
   - Machine learning-based assignment
   - Geographic distribution
   - Trading style-based grouping

4. **Account Pooling**
   - Shared accounts for small users
   - Dedicated accounts for high-volume traders
   - Automatic promotion/demotion based on activity

## 📞 Support

For issues with the multi-account system:

1. Check the troubleshooting section above
2. Run the test script to identify issues
3. Check application logs for detailed error information
4. Review environment variable configuration

## 📝 Configuration Examples

### Small Team (2-3 accounts)

```bash
# Primary account for general users
ALPACA_PAPER_API_KEY=PK_PRIMARY_KEY
ALPACA_PAPER_SECRET_KEY=PRIMARY_SECRET

# Account for power users
ALPACA_PAPER_API_KEY_1=PK_POWER_USER_KEY
ALPACA_PAPER_SECRET_KEY_1=POWER_USER_SECRET

# Account for testing/development
ALPACA_PAPER_API_KEY_2=PK_DEV_KEY
ALPACA_PAPER_SECRET_KEY_2=DEV_SECRET
```

### Large Organization (5+ accounts)

```bash
# Department-based accounts
ALPACA_PAPER_API_KEY=PK_TRADING_DEPT_KEY      # Trading department
ALPACA_PAPER_SECRET_KEY=TRADING_DEPT_SECRET

ALPACA_PAPER_API_KEY_1=PK_RESEARCH_DEPT_KEY   # Research department
ALPACA_PAPER_SECRET_KEY_1=RESEARCH_DEPT_SECRET

ALPACA_PAPER_API_KEY_2=PK_PORTFOLIO_MGMT_KEY  # Portfolio management
ALPACA_PAPER_SECRET_KEY_2=PORTFOLIO_MGMT_SECRET

ALPACA_PAPER_API_KEY_3=PK_RISK_MGMT_KEY       # Risk management
ALPACA_PAPER_SECRET_KEY_3=RISK_MGMT_SECRET

ALPACA_PAPER_API_KEY_4=PK_GENERAL_USERS_KEY   # General users
ALPACA_PAPER_SECRET_KEY_4=GENERAL_USERS_SECRET
```

This multi-account system provides the foundation for scalable, isolated trading operations while maintaining the simplicity and user experience of the original single-account system.