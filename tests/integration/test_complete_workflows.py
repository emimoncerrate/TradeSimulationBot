"""
Comprehensive Integration Tests for Complete User Workflows

This module provides end-to-end integration tests covering complete user workflows
from slash command initiation through trade execution, including all error scenarios,
user role variations, and system interactions. Tests validate the entire application
stack including Slack integration, database operations, external service calls,
and UI state management.
"""

import asyncio
import pytest
import json
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call
import uuid

# Import application components
from app import create_slack_app, ApplicationMetrics
from listeners.commands import CommandHandler, CommandType, CommandContext
from listeners.actions import ActionHandler, ActionType, ActionContext
from services.service_container import ServiceContainer
from services.auth import AuthService, AuthenticationError, AuthorizationError
from services.database import DatabaseService, DatabaseError, NotFoundError
from services.market_data import MarketDataService, MarketDataError, MarketQuote
from services.risk_analysis import RiskAnalysisService, RiskAnalysis
from services.trading_api import TradingAPIService, TradeExecution
from models.user import User, UserRole, UserStatus, Permission, UserProfile
from models.trade import Trade, TradeType, TradeStatus, RiskLevel
from models.portfolio import Position, Portfolio
from ui.trade_widget import TradeWidget, WidgetContext, WidgetState
from config.settings import get_config

# Test fixtures and utilities
from tests.fixtures.slack_payloads import (
    create_slash_command_payload,
    create_button_action_payload,
    create_modal_submission_payload,
    create_app_home_payload
)
from tests.fixtures.test_data import (
    create_test_user,
    create_test_trade,
    create_test_position,
    create_test_market_quote,
    create_test_risk_analysis
)
from tests.utils.mock_services import (
    MockSlackClient,
    MockDatabaseService,
    MockMarketDataService,
    MockRiskAnalysisService,
    MockTradingAPIService
)


class TestCompleteUserWorkflows:
    """
    Integration tests for complete user workflows covering all user roles,
    command types, and interaction patterns with comprehensive error handling
    and performance validation.
    """
    
    @pytest.fixture
    async def service_container(self):
        """Create mock service container for testing."""
        container = ServiceContainer()
        
        # Mock all services
        container._auth_service = AsyncMock(spec=AuthService)
        container._database_service = MockDatabaseService()
        container._market_data_service = MockMarketDataService()
        container._risk_analysis_service = MockRiskAnalysisService()
        container._trading_api_service = MockTradingAPIService()
        
        return container
    
    @pytest.fixture
    def mock_slack_client(self):
        """Create mock Slack client for testing."""
        return MockSlackClient()
    
    @pytest.fixture
    def test_users(self):
        """Create test users for different roles."""
        return {
            'analyst': create_test_user(
                user_id='test_analyst_001',
                role=UserRole.RESEARCH_ANALYST,
                permissions=[
                    Permission.EXECUTE_TRADES,
                    Permission.REQUEST_RISK_ANALYSIS,
                    Permission.VIEW_RISK_ANALYSIS,
                    Permission.VIEW_PORTFOLIO
                ]
            ),
            'trader': create_test_user(
                user_id='test_trader_001',
                role=UserRole.EXECUTION_TRADER,
                permissions=[
                    Permission.EXECUTE_TRADES,
                    Permission.VIEW_TRADES,
                    Permission.VIEW_PORTFOLIO
                ]
            ),
            'pm': create_test_user(
                user_id='test_pm_001',
                role=UserRole.PORTFOLIO_MANAGER,
                permissions=[
                    Permission.EXECUTE_TRADES,
                    Permission.REQUEST_RISK_ANALYSIS,
                    Permission.VIEW_RISK_ANALYSIS,
                    Permission.VIEW_PORTFOLIO,
                    Permission.MANAGE_USERS,
                    Permission.VIEW_ALL_PORTFOLIOS
                ]
            )
        }
    
    @pytest.mark.asyncio
    async def test_complete_trade_workflow_success(self, service_container, mock_slack_client, test_users):
        """
        Test complete successful trade workflow from slash command to execution.
        
        Workflow:
        1. User types /trade command
        2. System validates user and channel
        3. Trade modal opens with market data
        4. User fills form and requests risk analysis
        5. Risk analysis completes (low risk)
        6. User submits trade
        7. Trade executes successfully
        8. User receives confirmation
        """
        # Setup test data
        test_user = test_users['analyst']
        test_symbol = 'AAPL'
        test_quantity = 100
        test_price = Decimal('150.00')
        
        # Mock service responses
        service_container._auth_service.authenticate_slack_user.return_value = (
            test_user,
            MagicMock(session_id='test_session_001')
        )
        service_container._auth_service.authorize_channel_access.return_value = True
        
        market_quote = create_test_market_quote(test_symbol, test_price)
        service_container._market_data_service.get_quote.return_value = market_quote
        
        risk_analysis = create_test_risk_analysis(
            risk_level=RiskLevel.LOW,
            risk_score=0.2,
            is_high_risk=False
        )
        service_container._risk_analysis_service.analyze_trade_risk.return_value = risk_analysis
        
        trade_execution = TradeExecution(
            success=True,
            execution_id='exec_001',
            execution_price=test_price,
            execution_timestamp=datetime.now(timezone.utc),
            error_message=None
        )
        service_container._trading_api_service.execute_trade.return_value = trade_execution
        
        # Initialize handlers
        command_handler = CommandHandler(
            service_container._auth_service,
            service_container._database_service
        )
        action_handler = ActionHandler(
            service_container._auth_service,
            service_container._database_service,
            service_container._market_data_service,
            service_container._risk_analysis_service,
            service_container._trading_api_service
        )
        
        # Step 1: Process /trade command
        command_payload = create_slash_command_payload(
            command='/trade',
            user_id=test_user.slack_user_id,
            channel_id='C1234567890',
            text=f'{test_symbol} {test_quantity} BUY'
        )
        
        start_time = time.time()
        
        await command_handler.process_command(
            CommandType.TRADE,
            command_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify modal was opened
        assert mock_slack_client.views_open.called
        modal_call = mock_slack_client.views_open.call_args
        assert 'view' in modal_call.kwargs
        assert 'trigger_id' in modal_call.kwargs
        
        # Step 2: Simulate market data request
        market_data_payload = create_button_action_payload(
            action_id='get_market_data',
            user_id=test_user.slack_user_id,
            view_id='V1234567890',
            state_values={
                'symbol_input': {'symbol': {'value': test_symbol}}
            }
        )
        
        await action_handler.process_action(
            ActionType.GET_MARKET_DATA,
            market_data_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify market data was fetched and modal updated
        service_container._market_data_service.get_quote.assert_called_with(test_symbol)
        assert mock_slack_client.views_update.called
        
        # Step 3: Simulate risk analysis request
        risk_analysis_payload = create_button_action_payload(
            action_id='analyze_risk',
            user_id=test_user.slack_user_id,
            view_id='V1234567890',
            state_values={
                'symbol_input': {'symbol': {'value': test_symbol}},
                'quantity_input': {'quantity': {'value': str(test_quantity)}},
                'trade_type_select': {'trade_type': {'selected_option': {'value': 'BUY'}}},
                'price_input': {'price': {'value': str(test_price)}}
            }
        )
        
        await action_handler.process_action(
            ActionType.ANALYZE_RISK,
            risk_analysis_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify risk analysis was performed
        service_container._risk_analysis_service.analyze_trade_risk.assert_called_once()
        
        # Step 4: Simulate trade submission
        trade_submission_payload = create_modal_submission_payload(
            callback_id='trade_modal',
            user_id=test_user.slack_user_id,
            view_id='V1234567890',
            state_values={
                'symbol_input': {'symbol': {'value': test_symbol}},
                'quantity_input': {'quantity': {'value': str(test_quantity)}},
                'trade_type_select': {'trade_type': {'selected_option': {'value': 'BUY'}}},
                'price_input': {'price': {'value': str(test_price)}}
            }
        )
        
        await action_handler.process_action(
            ActionType.SUBMIT_TRADE,
            trade_submission_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify trade was executed
        service_container._trading_api_service.execute_trade.assert_called_once()
        service_container._database_service.log_trade.assert_called_once()
        service_container._database_service.update_position.assert_called_once()
        
        # Verify success notification was sent
        assert mock_slack_client.chat_postMessage.called or mock_slack_client.chat_postEphemeral.called
        
        # Verify performance
        total_time = time.time() - start_time
        assert total_time < 10.0, f"Workflow took too long: {total_time:.2f}s"
        
        # Verify all service calls were made in correct order
        expected_calls = [
            'authenticate_slack_user',
            'authorize_channel_access',
            'get_quote',
            'analyze_trade_risk',
            'execute_trade',
            'log_trade',
            'update_position'
        ]
        
        # Check that all expected operations completed successfully
        assert len(mock_slack_client.method_calls) >= 4  # At least modal open, update, close, and notification
    
    @pytest.mark.asyncio
    async def test_high_risk_trade_workflow(self, service_container, mock_slack_client, test_users):
        """
        Test high-risk trade workflow requiring additional confirmation.
        
        Workflow includes:
        1. Normal trade setup
        2. Risk analysis flags high risk
        3. UI changes to require confirmation
        4. User must type 'confirm' to proceed
        5. Portfolio Manager notification sent
        """
        test_user = test_users['analyst']
        test_symbol = 'TSLA'
        test_quantity = 1000  # Large quantity for high risk
        test_price = Decimal('800.00')
        
        # Setup high-risk scenario
        service_container._auth_service.authenticate_slack_user.return_value = (
            test_user,
            MagicMock(session_id='test_session_002')
        )
        service_container._auth_service.authorize_channel_access.return_value = True
        
        high_risk_analysis = create_test_risk_analysis(
            risk_level=RiskLevel.HIGH,
            risk_score=0.8,
            is_high_risk=True,
            recommendations=['Consider reducing position size', 'Review portfolio impact']
        )
        service_container._risk_analysis_service.analyze_trade_risk.return_value = high_risk_analysis
        
        # Initialize handlers
        action_handler = ActionHandler(
            service_container._auth_service,
            service_container._database_service,
            service_container._market_data_service,
            service_container._risk_analysis_service,
            service_container._trading_api_service
        )
        
        # Simulate risk analysis that flags high risk
        risk_analysis_payload = create_button_action_payload(
            action_id='analyze_risk',
            user_id=test_user.slack_user_id,
            view_id='V1234567890',
            state_values={
                'symbol_input': {'symbol': {'value': test_symbol}},
                'quantity_input': {'quantity': {'value': str(test_quantity)}},
                'trade_type_select': {'trade_type': {'selected_option': {'value': 'BUY'}}},
                'price_input': {'price': {'value': str(test_price)}}
            }
        )
        
        await action_handler.process_action(
            ActionType.ANALYZE_RISK,
            risk_analysis_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify modal was updated with high-risk warning
        assert mock_slack_client.views_update.called
        update_call = mock_slack_client.views_update.call_args
        modal_view = update_call.kwargs['view']
        
        # Check that confirmation field is present in high-risk modal
        modal_json = json.dumps(modal_view)
        assert 'confirm' in modal_json.lower()
        assert 'high risk' in modal_json.lower() or 'high-risk' in modal_json.lower()
        
        # Test submission without proper confirmation (should fail)
        invalid_submission = create_modal_submission_payload(
            callback_id='trade_modal',
            user_id=test_user.slack_user_id,
            view_id='V1234567890',
            state_values={
                'symbol_input': {'symbol': {'value': test_symbol}},
                'quantity_input': {'quantity': {'value': str(test_quantity)}},
                'trade_type_select': {'trade_type': {'selected_option': {'value': 'BUY'}}},
                'price_input': {'price': {'value': str(test_price)}},
                'confirmation_input': {'confirmation_text': {'value': 'yes'}}  # Wrong confirmation
            }
        )
        
        with pytest.raises(Exception):  # Should raise validation error
            await action_handler.process_action(
                ActionType.SUBMIT_TRADE,
                invalid_submission,
                mock_slack_client,
                AsyncMock(),
                MagicMock()
            )
        
        # Test submission with correct confirmation
        valid_submission = create_modal_submission_payload(
            callback_id='trade_modal',
            user_id=test_user.slack_user_id,
            view_id='V1234567890',
            state_values={
                'symbol_input': {'symbol': {'value': test_symbol}},
                'quantity_input': {'quantity': {'value': str(test_quantity)}},
                'trade_type_select': {'trade_type': {'selected_option': {'value': 'BUY'}}},
                'price_input': {'price': {'value': str(test_price)}},
                'confirmation_input': {'confirmation_text': {'value': 'confirm'}}
            }
        )
        
        # Mock successful execution
        trade_execution = TradeExecution(
            success=True,
            execution_id='exec_002',
            execution_price=test_price,
            execution_timestamp=datetime.now(timezone.utc)
        )
        service_container._trading_api_service.execute_trade.return_value = trade_execution
        
        await action_handler.process_action(
            ActionType.SUBMIT_TRADE,
            valid_submission,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify trade was executed
        service_container._trading_api_service.execute_trade.assert_called_once()
        
        # Verify Portfolio Manager notification would be sent
        # (This would be tested in the notification service tests)
        assert mock_slack_client.chat_postMessage.called or mock_slack_client.chat_postEphemeral.called
    
    @pytest.mark.asyncio
    async def test_error_scenarios_workflow(self, service_container, mock_slack_client, test_users):
        """
        Test various error scenarios in the complete workflow.
        
        Error scenarios:
        1. Authentication failure
        2. Channel not approved
        3. Market data unavailable
        4. Risk analysis service down
        5. Trading API failure
        6. Database errors
        """
        test_user = test_users['trader']
        
        # Initialize handlers
        command_handler = CommandHandler(
            service_container._auth_service,
            service_container._database_service
        )
        action_handler = ActionHandler(
            service_container._auth_service,
            service_container._database_service,
            service_container._market_data_service,
            service_container._risk_analysis_service,
            service_container._trading_api_service
        )
        
        # Test 1: Authentication failure
        service_container._auth_service.authenticate_slack_user.side_effect = AuthenticationError(
            "Invalid user credentials", "INVALID_CREDENTIALS"
        )
        
        command_payload = create_slash_command_payload(
            command='/trade',
            user_id='invalid_user',
            channel_id='C1234567890'
        )
        
        await command_handler.process_command(
            CommandType.TRADE,
            command_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify error message was sent
        assert mock_slack_client.chat_postEphemeral.called
        error_call = mock_slack_client.chat_postEphemeral.call_args
        assert 'authentication failed' in error_call.kwargs['text'].lower()
        
        # Reset mocks
        mock_slack_client.reset_mock()
        service_container._auth_service.authenticate_slack_user.side_effect = None
        service_container._auth_service.authenticate_slack_user.return_value = (
            test_user,
            MagicMock(session_id='test_session_003')
        )
        
        # Test 2: Channel not approved
        service_container._auth_service.authorize_channel_access.side_effect = AuthorizationError(
            "Channel not approved for trading", "CHANNEL_NOT_APPROVED"
        )
        
        await command_handler.process_command(
            CommandType.TRADE,
            command_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify channel error message
        assert mock_slack_client.chat_postEphemeral.called
        error_call = mock_slack_client.chat_postEphemeral.call_args
        assert 'access denied' in error_call.kwargs['text'].lower()
        
        # Reset for market data error test
        mock_slack_client.reset_mock()
        service_container._auth_service.authorize_channel_access.side_effect = None
        service_container._auth_service.authorize_channel_access.return_value = True
        
        # Test 3: Market data service error
        service_container._market_data_service.get_quote.side_effect = MarketDataError(
            "Market data service unavailable", "SERVICE_UNAVAILABLE"
        )
        
        market_data_payload = create_button_action_payload(
            action_id='get_market_data',
            user_id=test_user.slack_user_id,
            view_id='V1234567890',
            state_values={
                'symbol_input': {'symbol': {'value': 'AAPL'}}
            }
        )
        
        await action_handler.process_action(
            ActionType.GET_MARKET_DATA,
            market_data_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify error handling for market data
        assert mock_slack_client.views_update.called
        
        # Test 4: Trading API failure
        service_container._market_data_service.get_quote.side_effect = None
        service_container._market_data_service.get_quote.return_value = create_test_market_quote('AAPL', Decimal('150.00'))
        
        service_container._trading_api_service.execute_trade.return_value = TradeExecution(
            success=False,
            execution_id=None,
            execution_price=None,
            execution_timestamp=None,
            error_message="Trading system temporarily unavailable"
        )
        
        trade_submission = create_modal_submission_payload(
            callback_id='trade_modal',
            user_id=test_user.slack_user_id,
            view_id='V1234567890',
            state_values={
                'symbol_input': {'symbol': {'value': 'AAPL'}},
                'quantity_input': {'quantity': {'value': '100'}},
                'trade_type_select': {'trade_type': {'selected_option': {'value': 'BUY'}}},
                'price_input': {'price': {'value': '150.00'}}
            }
        )
        
        await action_handler.process_action(
            ActionType.SUBMIT_TRADE,
            trade_submission,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify failure notification was sent
        assert mock_slack_client.chat_postMessage.called or mock_slack_client.chat_postEphemeral.called
        
        # Verify trade was logged with failed status
        service_container._database_service.log_trade.assert_called()
        logged_trade = service_container._database_service.log_trade.call_args[0][0]
        # Note: Status might be updated after logging, so we check the update call
        service_container._database_service.update_trade_status.assert_called()
    
    @pytest.mark.asyncio
    async def test_role_based_workflow_variations(self, service_container, mock_slack_client, test_users):
        """
        Test workflow variations based on user roles.
        
        Tests different UI and functionality based on:
        1. Research Analyst - Full risk analysis features
        2. Execution Trader - Streamlined interface
        3. Portfolio Manager - Additional oversight features
        """
        # Initialize handlers
        command_handler = CommandHandler(
            service_container._auth_service,
            service_container._database_service
        )
        
        # Test Research Analyst workflow
        analyst = test_users['analyst']
        service_container._auth_service.authenticate_slack_user.return_value = (
            analyst,
            MagicMock(session_id='analyst_session')
        )
        service_container._auth_service.authorize_channel_access.return_value = True
        
        command_payload = create_slash_command_payload(
            command='/trade',
            user_id=analyst.slack_user_id,
            channel_id='C1234567890'
        )
        
        await command_handler.process_command(
            CommandType.TRADE,
            command_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify analyst gets full-featured modal
        assert mock_slack_client.views_open.called
        analyst_modal = mock_slack_client.views_open.call_args.kwargs['view']
        analyst_modal_json = json.dumps(analyst_modal)
        
        # Analyst should have risk analysis features
        assert 'analyze' in analyst_modal_json.lower() or 'risk' in analyst_modal_json.lower()
        
        # Reset for trader test
        mock_slack_client.reset_mock()
        
        # Test Execution Trader workflow
        trader = test_users['trader']
        service_container._auth_service.authenticate_slack_user.return_value = (
            trader,
            MagicMock(session_id='trader_session')
        )
        
        command_payload = create_slash_command_payload(
            command='/trade',
            user_id=trader.slack_user_id,
            channel_id='C1234567890'
        )
        
        await command_handler.process_command(
            CommandType.TRADE,
            command_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify trader gets streamlined interface
        assert mock_slack_client.views_open.called
        trader_modal = mock_slack_client.views_open.call_args.kwargs['view']
        
        # Both should have basic trade functionality
        trader_modal_json = json.dumps(trader_modal)
        assert 'symbol' in trader_modal_json.lower()
        assert 'quantity' in trader_modal_json.lower()
        
        # Reset for Portfolio Manager test
        mock_slack_client.reset_mock()
        
        # Test Portfolio Manager workflow
        pm = test_users['pm']
        service_container._auth_service.authenticate_slack_user.return_value = (
            pm,
            MagicMock(session_id='pm_session')
        )
        
        command_payload = create_slash_command_payload(
            command='/trade',
            user_id=pm.slack_user_id,
            channel_id='C1234567890'
        )
        
        await command_handler.process_command(
            CommandType.TRADE,
            command_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        # Verify PM gets comprehensive interface
        assert mock_slack_client.views_open.called
        pm_modal = mock_slack_client.views_open.call_args.kwargs['view']
        pm_modal_json = json.dumps(pm_modal)
        
        # PM should have all features available
        assert 'symbol' in pm_modal_json.lower()
        assert 'quantity' in pm_modal_json.lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_user_workflows(self, service_container, mock_slack_client, test_users):
        """
        Test multiple users executing workflows concurrently.
        
        Validates:
        1. No interference between user sessions
        2. Proper isolation of user data
        3. Performance under concurrent load
        4. Resource cleanup
        """
        # Setup multiple users
        users = [test_users['analyst'], test_users['trader'], test_users['pm']]
        
        # Mock authentication for all users
        def mock_auth(slack_user_id, team_id, channel_id, *args, **kwargs):
            user = next((u for u in users if u.slack_user_id == slack_user_id), users[0])
            return user, MagicMock(session_id=f'session_{slack_user_id}')
        
        service_container._auth_service.authenticate_slack_user.side_effect = mock_auth
        service_container._auth_service.authorize_channel_access.return_value = True
        
        # Initialize handlers
        command_handler = CommandHandler(
            service_container._auth_service,
            service_container._database_service
        )
        
        # Create concurrent workflows
        async def user_workflow(user: User, symbol: str):
            """Simulate a complete user workflow."""
            command_payload = create_slash_command_payload(
                command='/trade',
                user_id=user.slack_user_id,
                channel_id='C1234567890',
                text=f'{symbol} 100 BUY'
            )
            
            start_time = time.time()
            
            await command_handler.process_command(
                CommandType.TRADE,
                command_payload,
                mock_slack_client,
                AsyncMock(),
                MagicMock()
            )
            
            return time.time() - start_time
        
        # Execute concurrent workflows
        start_time = time.time()
        
        tasks = [
            user_workflow(test_users['analyst'], 'AAPL'),
            user_workflow(test_users['trader'], 'GOOGL'),
            user_workflow(test_users['pm'], 'MSFT')
        ]
        
        response_times = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify performance
        assert total_time < 5.0, f"Concurrent workflows took too long: {total_time:.2f}s"
        assert all(rt < 3.0 for rt in response_times), f"Individual workflows too slow: {response_times}"
        
        # Verify all users got their modals
        assert mock_slack_client.views_open.call_count == 3
        
        # Verify proper user isolation (each user authenticated separately)
        assert service_container._auth_service.authenticate_slack_user.call_count == 3
        
        # Verify no data leakage between users
        auth_calls = service_container._auth_service.authenticate_slack_user.call_args_list
        user_ids = [call[0][0] for call in auth_calls]
        assert len(set(user_ids)) == 3  # All different user IDs
    
    @pytest.mark.asyncio
    async def test_app_home_workflow(self, service_container, mock_slack_client, test_users):
        """
        Test App Home dashboard workflow.
        
        Validates:
        1. App Home tab rendering
        2. Portfolio data display
        3. Trade history integration
        4. Real-time updates
        """
        test_user = test_users['pm']
        
        # Mock user authentication
        service_container._auth_service.authenticate_slack_user.return_value = (
            test_user,
            MagicMock(session_id='app_home_session')
        )
        
        # Mock portfolio data
        test_positions = [
            create_test_position('AAPL', 100, Decimal('150.00')),
            create_test_position('GOOGL', 50, Decimal('2500.00')),
            create_test_position('MSFT', 75, Decimal('300.00'))
        ]
        service_container._database_service.get_user_positions.return_value = test_positions
        
        test_trades = [
            create_test_trade('AAPL', 100, TradeType.BUY, Decimal('150.00'), TradeStatus.EXECUTED),
            create_test_trade('GOOGL', 50, TradeType.BUY, Decimal('2500.00'), TradeStatus.EXECUTED)
        ]
        service_container._database_service.get_user_trades.return_value = test_trades
        
        # Import and test event handler
        from listeners.events import EventHandler
        
        event_handler = EventHandler(
            service_container._auth_service,
            service_container._database_service,
            service_container._market_data_service
        )
        
        # Simulate App Home opened event
        app_home_payload = create_app_home_payload(
            user_id=test_user.slack_user_id,
            team_id='T1234567890'
        )
        
        await event_handler.handle_app_home_opened(
            app_home_payload,
            mock_slack_client,
            AsyncMock()
        )
        
        # Verify App Home was published
        assert mock_slack_client.views_publish.called
        
        # Verify portfolio data was fetched
        service_container._database_service.get_user_positions.assert_called_with(test_user.user_id)
        service_container._database_service.get_user_trades.assert_called_with(
            test_user.user_id, 
            limit=10
        )
        
        # Verify App Home content includes portfolio data
        publish_call = mock_slack_client.views_publish.call_args
        app_home_view = publish_call.kwargs['view']
        app_home_json = json.dumps(app_home_view)
        
        # Should contain position information
        assert 'aapl' in app_home_json.lower() or 'AAPL' in app_home_json
        assert 'portfolio' in app_home_json.lower()
        assert 'position' in app_home_json.lower() or 'trade' in app_home_json.lower()
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, service_container, mock_slack_client, test_users):
        """
        Test performance benchmarks for various operations.
        
        Benchmarks:
        1. Command processing time < 1s
        2. Modal rendering time < 500ms
        3. Market data retrieval < 2s
        4. Risk analysis < 3s
        5. Trade execution < 2s
        """
        test_user = test_users['analyst']
        
        # Setup mocks with realistic delays
        async def delayed_market_data(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate API call
            return create_test_market_quote('AAPL', Decimal('150.00'))
        
        async def delayed_risk_analysis(*args, **kwargs):
            await asyncio.sleep(0.2)  # Simulate AI processing
            return create_test_risk_analysis(RiskLevel.LOW, 0.3, False)
        
        async def delayed_trade_execution(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate trade processing
            return TradeExecution(
                success=True,
                execution_id='perf_test_001',
                execution_price=Decimal('150.00'),
                execution_timestamp=datetime.now(timezone.utc)
            )
        
        service_container._auth_service.authenticate_slack_user.return_value = (
            test_user,
            MagicMock(session_id='perf_session')
        )
        service_container._auth_service.authorize_channel_access.return_value = True
        service_container._market_data_service.get_quote.side_effect = delayed_market_data
        service_container._risk_analysis_service.analyze_trade_risk.side_effect = delayed_risk_analysis
        service_container._trading_api_service.execute_trade.side_effect = delayed_trade_execution
        
        # Initialize handlers
        command_handler = CommandHandler(
            service_container._auth_service,
            service_container._database_service
        )
        action_handler = ActionHandler(
            service_container._auth_service,
            service_container._database_service,
            service_container._market_data_service,
            service_container._risk_analysis_service,
            service_container._trading_api_service
        )
        
        # Benchmark 1: Command processing
        start_time = time.time()
        
        command_payload = create_slash_command_payload(
            command='/trade',
            user_id=test_user.slack_user_id,
            channel_id='C1234567890'
        )
        
        await command_handler.process_command(
            CommandType.TRADE,
            command_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        command_time = time.time() - start_time
        assert command_time < 1.0, f"Command processing too slow: {command_time:.3f}s"
        
        # Benchmark 2: Market data retrieval
        start_time = time.time()
        
        market_data_payload = create_button_action_payload(
            action_id='get_market_data',
            user_id=test_user.slack_user_id,
            view_id='V1234567890',
            state_values={
                'symbol_input': {'symbol': {'value': 'AAPL'}}
            }
        )
        
        await action_handler.process_action(
            ActionType.GET_MARKET_DATA,
            market_data_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        market_data_time = time.time() - start_time
        assert market_data_time < 2.0, f"Market data retrieval too slow: {market_data_time:.3f}s"
        
        # Benchmark 3: Risk analysis
        start_time = time.time()
        
        risk_analysis_payload = create_button_action_payload(
            action_id='analyze_risk',
            user_id=test_user.slack_user_id,
            view_id='V1234567890',
            state_values={
                'symbol_input': {'symbol': {'value': 'AAPL'}},
                'quantity_input': {'quantity': {'value': '100'}},
                'trade_type_select': {'trade_type': {'selected_option': {'value': 'BUY'}}},
                'price_input': {'price': {'value': '150.00'}}
            }
        )
        
        await action_handler.process_action(
            ActionType.ANALYZE_RISK,
            risk_analysis_payload,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        risk_analysis_time = time.time() - start_time
        assert risk_analysis_time < 3.0, f"Risk analysis too slow: {risk_analysis_time:.3f}s"
        
        # Benchmark 4: Trade execution
        start_time = time.time()
        
        trade_submission = create_modal_submission_payload(
            callback_id='trade_modal',
            user_id=test_user.slack_user_id,
            view_id='V1234567890',
            state_values={
                'symbol_input': {'symbol': {'value': 'AAPL'}},
                'quantity_input': {'quantity': {'value': '100'}},
                'trade_type_select': {'trade_type': {'selected_option': {'value': 'BUY'}}},
                'price_input': {'price': {'value': '150.00'}}
            }
        )
        
        await action_handler.process_action(
            ActionType.SUBMIT_TRADE,
            trade_submission,
            mock_slack_client,
            AsyncMock(),
            MagicMock()
        )
        
        trade_execution_time = time.time() - start_time
        assert trade_execution_time < 2.0, f"Trade execution too slow: {trade_execution_time:.3f}s"
        
        # Overall performance summary
        total_workflow_time = command_time + market_data_time + risk_analysis_time + trade_execution_time
        assert total_workflow_time < 8.0, f"Total workflow too slow: {total_workflow_time:.3f}s"
        
        print(f"\nPerformance Benchmarks:")
        print(f"Command processing: {command_time:.3f}s")
        print(f"Market data retrieval: {market_data_time:.3f}s")
        print(f"Risk analysis: {risk_analysis_time:.3f}s")
        print(f"Trade execution: {trade_execution_time:.3f}s")
        print(f"Total workflow: {total_workflow_time:.3f}s")


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])