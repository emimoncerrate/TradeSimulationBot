"""
Tests for enhanced /trade command with live market data features.

This test suite validates the enhanced market data display, real-time updates,
interactive features, and user experience improvements.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from listeners.enhanced_trade_command import (
    EnhancedTradeCommand, 
    EnhancedMarketContext, 
    MarketDataView,
    TimeFrame
)
from services.market_data import MarketQuote, MarketStatus, DataQuality
from models.user import User, UserRole, Permission


class TestEnhancedTradeCommand:
    """Test suite for enhanced trade command."""
    
    @pytest.fixture
    def mock_market_data_service(self):
        """Mock market data service."""
        service = AsyncMock()
        
        # Mock AAPL quote
        service.get_quote.return_value = MarketQuote(
            symbol="AAPL",
            current_price=Decimal("150.25"),
            open_price=Decimal("148.50"),
            high_price=Decimal("151.75"),
            low_price=Decimal("147.80"),
            previous_close=Decimal("149.00"),
            volume=45_000_000,
            market_cap=2_400_000_000_000,
            pe_ratio=Decimal("28.5"),
            market_status=MarketStatus.OPEN,
            data_quality=DataQuality.REAL_TIME,
            exchange="NASDAQ",
            api_latency_ms=125.0
        )
        
        return service
    
    @pytest.fixture
    def mock_auth_service(self):
        """Mock authentication service."""
        service = AsyncMock()
        
        # Mock user with market data permissions
        user = User(
            user_id="U123456789",
            team_id="T123456789",
            username="testuser",
            email="test@example.com",
            role=UserRole.PORTFOLIO_MANAGER,
            permissions=[Permission.VIEW_MARKET_DATA, Permission.EXECUTE_TRADES]
        )
        
        service.authenticate_user.return_value = user
        return service
    
    @pytest.fixture
    def enhanced_command(self, mock_market_data_service, mock_auth_service):
        """Create enhanced trade command instance."""
        return EnhancedTradeCommand(mock_market_data_service, mock_auth_service)
    
    @pytest.fixture
    def sample_command_body(self):
        """Sample Slack command body."""
        return {
            "user_id": "U123456789",
            "team_id": "T123456789",
            "channel_id": "C123456789",
            "trigger_id": "trigger123",
            "text": "AAPL"
        }
    
    @pytest.fixture
    def mock_slack_client(self):
        """Mock Slack WebClient."""
        client = AsyncMock()
        client.views_open = AsyncMock()
        client.views_update = AsyncMock()
        client.chat_postEphemeral = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_handle_trade_command_with_symbol(self, enhanced_command, sample_command_body, mock_slack_client):
        """Test handling trade command with symbol parameter."""
        ack = AsyncMock()
        context = MagicMock()
        
        await enhanced_command.handle_trade_command(ack, sample_command_body, mock_slack_client, context)
        
        # Verify acknowledgment
        ack.assert_called_once()
        
        # Verify market data was fetched
        enhanced_command.market_data_service.get_quote.assert_called_once_with("AAPL")
        
        # Verify modal was opened
        mock_slack_client.views_open.assert_called_once()
        
        # Verify session was created
        session_key = "U123456789_C123456789"
        assert session_key in enhanced_command.active_sessions
        
        # Verify market context
        context = enhanced_command.active_sessions[session_key]
        assert context.symbol == "AAPL"
        assert context.current_quote is not None
        assert context.current_quote.symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_handle_trade_command_without_symbol(self, enhanced_command, mock_slack_client):
        """Test handling trade command without symbol parameter."""
        ack = AsyncMock()
        context = MagicMock()
        
        command_body = {
            "user_id": "U123456789",
            "team_id": "T123456789",
            "channel_id": "C123456789",
            "trigger_id": "trigger123",
            "text": ""
        }
        
        await enhanced_command.handle_trade_command(ack, command_body, mock_slack_client, context)
        
        # Verify acknowledgment
        ack.assert_called_once()
        
        # Verify no market data was fetched
        enhanced_command.market_data_service.get_quote.assert_not_called()
        
        # Verify modal was still opened (for symbol input)
        mock_slack_client.views_open.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_market_data_success(self, enhanced_command):
        """Test successful market data fetching."""
        context = EnhancedMarketContext(
            user=MagicMock(),
            channel_id="C123456789",
            trigger_id="trigger123",
            symbol="AAPL"
        )
        
        await enhanced_command._fetch_market_data(context)
        
        # Verify market data was fetched and stored
        assert context.current_quote is not None
        assert context.current_quote.symbol == "AAPL"
        assert context.current_quote.current_price == Decimal("150.25")
        assert context.error_message is None
        assert context.last_updated is not None
    
    @pytest.mark.asyncio
    async def test_fetch_market_data_error(self, enhanced_command):
        """Test market data fetching with error."""
        # Configure service to raise error
        enhanced_command.market_data_service.get_quote.side_effect = Exception("API Error")
        
        context = EnhancedMarketContext(
            user=MagicMock(),
            channel_id="C123456789",
            trigger_id="trigger123",
            symbol="INVALID"
        )
        
        await enhanced_command._fetch_market_data(context)
        
        # Verify error was handled
        assert context.current_quote is None
        assert context.error_message is not None
        assert "Unexpected error fetching market data" in context.error_message
    
    @pytest.mark.asyncio
    async def test_create_enhanced_market_modal_with_data(self, enhanced_command):
        """Test creating enhanced market modal with market data."""
        quote = MarketQuote(
            symbol="AAPL",
            current_price=Decimal("150.25"),
            open_price=Decimal("148.50"),
            high_price=Decimal("151.75"),
            low_price=Decimal("147.80"),
            previous_close=Decimal("149.00"),
            volume=45_000_000,
            market_status=MarketStatus.OPEN,
            data_quality=DataQuality.REAL_TIME
        )
        
        context = EnhancedMarketContext(
            user=MagicMock(),
            channel_id="C123456789",
            trigger_id="trigger123",
            symbol="AAPL",
            current_quote=quote,
            last_updated=datetime.utcnow()
        )
        
        modal = await enhanced_command._create_enhanced_market_modal(context)
        
        # Verify modal structure
        assert modal["type"] == "modal"
        assert modal["callback_id"] == "enhanced_trade_modal"
        assert "📊 Live Market Data" in modal["title"]["text"]
        assert "blocks" in modal
        assert len(modal["blocks"]) > 0
        
        # Verify market data is displayed
        blocks_text = str(modal["blocks"])
        assert "AAPL" in blocks_text
        assert "150.25" in blocks_text
        assert "LIVE" in blocks_text
    
    @pytest.mark.asyncio
    async def test_create_enhanced_market_modal_without_data(self, enhanced_command):
        """Test creating enhanced market modal without market data."""
        context = EnhancedMarketContext(
            user=MagicMock(),
            channel_id="C123456789",
            trigger_id="trigger123"
        )
        
        modal = await enhanced_command._create_enhanced_market_modal(context)
        
        # Verify modal structure
        assert modal["type"] == "modal"
        assert modal["callback_id"] == "enhanced_trade_modal"
        assert "blocks" in modal
        
        # Verify no submit button without market data
        assert modal.get("submit") is None
    
    def test_extract_symbol_valid(self, enhanced_command):
        """Test extracting valid symbol from command text."""
        test_cases = [
            ("AAPL", "AAPL"),
            ("aapl", "AAPL"),
            ("trade TSLA", "TRADE"),  # First valid symbol
            ("buy 100 MSFT", "BUY"),  # First valid symbol
            ("GOOGL 150", "GOOGL"),
            ("", None),
            ("123 456", None),
            ("TOOLONGNAME", None)
        ]
        
        for input_text, expected in test_cases:
            result = enhanced_command._extract_symbol(input_text)
            assert result == expected
    
    def test_get_price_change_emoji(self, enhanced_command):
        """Test price change emoji selection."""
        # Positive change
        quote_up = MarketQuote(
            symbol="TEST",
            current_price=Decimal("100"),
            previous_close=Decimal("95")
        )
        assert enhanced_command._get_price_change_emoji(quote_up) == "📈"
        
        # Negative change
        quote_down = MarketQuote(
            symbol="TEST",
            current_price=Decimal("95"),
            previous_close=Decimal("100")
        )
        assert enhanced_command._get_price_change_emoji(quote_down) == "📉"
        
        # No change
        quote_flat = MarketQuote(
            symbol="TEST",
            current_price=Decimal("100"),
            previous_close=Decimal("100")
        )
        assert enhanced_command._get_price_change_emoji(quote_flat) == "➡️"
    
    def test_format_price_change(self, enhanced_command):
        """Test price change formatting."""
        quote = MarketQuote(
            symbol="TEST",
            current_price=Decimal("102.50"),
            previous_close=Decimal("100.00")
        )
        
        result = enhanced_command._format_price_change(quote)
        assert "+$2.50" in result
        assert "+2.50%" in result
    
    def test_format_market_cap(self, enhanced_command):
        """Test market cap formatting."""
        test_cases = [
            (2_400_000_000_000, "$2.40T"),  # Trillion
            (150_000_000_000, "$150.00B"),  # Billion
            (5_000_000_000, "$5.00B"),      # Billion
            (500_000_000, "$500.00M"),      # Million
            (50_000_000, "$50.00M"),        # Million
            (1_000_000, "$1.00M"),          # Million
            (500_000, "$500,000")           # Less than million
        ]
        
        for market_cap, expected in test_cases:
            result = enhanced_command._format_market_cap(market_cap)
            assert result == expected
    
    def test_get_market_status_emoji(self, enhanced_command):
        """Test market status emoji selection."""
        test_cases = [
            (MarketStatus.OPEN, "🟢"),
            (MarketStatus.CLOSED, "🔴"),
            (MarketStatus.PRE_MARKET, "🟡"),
            (MarketStatus.AFTER_HOURS, "🟠"),
            (MarketStatus.HOLIDAY, "🔵"),
            (MarketStatus.UNKNOWN, "⚪")
        ]
        
        for status, expected_emoji in test_cases:
            result = enhanced_command._get_market_status_emoji(status)
            assert result == expected_emoji
    
    def test_get_data_quality_emoji(self, enhanced_command):
        """Test data quality emoji selection."""
        test_cases = [
            (DataQuality.REAL_TIME, "⚡"),
            (DataQuality.DELAYED, "⏰"),
            (DataQuality.STALE, "⚠️"),
            (DataQuality.CACHED, "💾"),
            (DataQuality.FALLBACK, "🔄")
        ]
        
        for quality, expected_emoji in test_cases:
            result = enhanced_command._get_data_quality_emoji(quality)
            assert result == expected_emoji
    
    @pytest.mark.asyncio
    async def test_authentication_failure(self, enhanced_command, mock_slack_client):
        """Test handling authentication failure."""
        # Configure auth service to raise error
        enhanced_command.auth_service.authenticate_user.side_effect = Exception("Auth failed")
        
        ack = AsyncMock()
        context = MagicMock()
        
        command_body = {
            "user_id": "U123456789",
            "team_id": "T123456789",
            "channel_id": "C123456789",
            "trigger_id": "trigger123",
            "text": "AAPL"
        }
        
        await enhanced_command.handle_trade_command(ack, command_body, mock_slack_client, context)
        
        # Verify error response was sent
        mock_slack_client.chat_postEphemeral.assert_called_once()
        call_args = mock_slack_client.chat_postEphemeral.call_args[1]
        assert "Error" in call_args["text"]
    
    @pytest.mark.asyncio
    async def test_insufficient_permissions(self, enhanced_command, mock_slack_client):
        """Test handling insufficient permissions."""
        # Create user without market data permissions
        user_no_perms = User(
            user_id="U123456789",
            team_id="T123456789",
            username="testuser",
            email="test@example.com",
            role=UserRole.RESEARCH_ANALYST,
            permissions=[]  # No permissions
        )
        
        enhanced_command.auth_service.authenticate_user.return_value = user_no_perms
        
        ack = AsyncMock()
        context = MagicMock()
        
        command_body = {
            "user_id": "U123456789",
            "team_id": "T123456789",
            "channel_id": "C123456789",
            "trigger_id": "trigger123",
            "text": "AAPL"
        }
        
        await enhanced_command.handle_trade_command(ack, command_body, mock_slack_client, context)
        
        # Verify error response was sent
        mock_slack_client.chat_postEphemeral.assert_called_once()
        call_args = mock_slack_client.chat_postEphemeral.call_args[1]
        assert "Insufficient permissions" in call_args["text"]


class TestEnhancedMarketContext:
    """Test suite for enhanced market context."""
    
    def test_context_initialization(self):
        """Test context initialization with defaults."""
        user = MagicMock()
        context = EnhancedMarketContext(
            user=user,
            channel_id="C123456789",
            trigger_id="trigger123"
        )
        
        assert context.user == user
        assert context.channel_id == "C123456789"
        assert context.trigger_id == "trigger123"
        assert context.symbol is None
        assert context.current_quote is None
        assert context.view_type == MarketDataView.OVERVIEW
        assert context.time_frame == TimeFrame.REAL_TIME
        assert context.auto_refresh is True
        assert context.refresh_interval == 30
        assert context.historical_quotes == []
        assert context.price_alerts == []
        assert context.watch_list == []
    
    def test_context_with_symbol(self):
        """Test context initialization with symbol."""
        user = MagicMock()
        context = EnhancedMarketContext(
            user=user,
            channel_id="C123456789",
            trigger_id="trigger123",
            symbol="AAPL"
        )
        
        assert context.symbol == "AAPL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])