"""
Test suite for Risk Alert feature.

Tests cover alert creation, monitoring, triggering, and management.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from models.risk_alert import RiskAlertConfig, AlertStatus, RiskAlertValidationError
from models.trade import Trade, TradeType, TradeStatus
from services.alert_monitor import RiskAlertMonitor
from services.database import DatabaseService


class TestRiskAlertConfig:
    """Test RiskAlertConfig model."""
    
    def test_create_valid_alert(self):
        """Test creating a valid risk alert."""
        alert = RiskAlertConfig(
            manager_id="U123456",
            trade_size_threshold=Decimal('100000'),
            loss_percent_threshold=Decimal('5'),
            vix_threshold=Decimal('20'),
            name="Test Alert"
        )
        
        assert alert.manager_id == "U123456"
        assert alert.trade_size_threshold == Decimal('100000')
        assert alert.loss_percent_threshold == Decimal('5')
        assert alert.vix_threshold == Decimal('20')
        assert alert.status == AlertStatus.ACTIVE
        assert alert.is_active() == True
    
    def test_invalid_trade_size(self):
        """Test validation for invalid trade size."""
        with pytest.raises(RiskAlertValidationError) as exc_info:
            RiskAlertConfig(
                manager_id="U123456",
                trade_size_threshold=Decimal('-1000'),
                loss_percent_threshold=Decimal('5'),
                vix_threshold=Decimal('20')
            )
        
        assert "positive" in str(exc_info.value.message).lower()
    
    def test_invalid_loss_percent(self):
        """Test validation for invalid loss percentage."""
        with pytest.raises(RiskAlertValidationError) as exc_info:
            RiskAlertConfig(
                manager_id="U123456",
                trade_size_threshold=Decimal('100000'),
                loss_percent_threshold=Decimal('150'),
                vix_threshold=Decimal('20')
            )
        
        assert "100" in str(exc_info.value.message)
    
    def test_matches_criteria(self):
        """Test criteria matching logic."""
        alert = RiskAlertConfig(
            manager_id="U123456",
            trade_size_threshold=Decimal('100000'),
            loss_percent_threshold=Decimal('5'),
            vix_threshold=Decimal('20')
        )
        
        # Should match
        assert alert.matches_criteria(
            trade_size=Decimal('150000'),
            loss_percent=Decimal('7'),
            vix_level=Decimal('25')
        ) == True
        
        # Should not match - trade size too small
        assert alert.matches_criteria(
            trade_size=Decimal('50000'),
            loss_percent=Decimal('7'),
            vix_level=Decimal('25')
        ) == False
        
        # Should not match - VIX too low
        assert alert.matches_criteria(
            trade_size=Decimal('150000'),
            loss_percent=Decimal('7'),
            vix_level=Decimal('15')
        ) == False
    
    def test_pause_resume(self):
        """Test pausing and resuming alerts."""
        alert = RiskAlertConfig(
            manager_id="U123456",
            trade_size_threshold=Decimal('100000'),
            loss_percent_threshold=Decimal('5'),
            vix_threshold=Decimal('20')
        )
        
        assert alert.is_active() == True
        
        alert.pause()
        assert alert.status == AlertStatus.PAUSED
        assert alert.is_active() == False
        
        alert.resume()
        assert alert.status == AlertStatus.ACTIVE
        assert alert.is_active() == True
    
    def test_record_trigger(self):
        """Test recording alert triggers."""
        alert = RiskAlertConfig(
            manager_id="U123456",
            trade_size_threshold=Decimal('100000'),
            loss_percent_threshold=Decimal('5'),
            vix_threshold=Decimal('20')
        )
        
        assert alert.trigger_count == 0
        assert alert.last_triggered_at is None
        
        alert.record_trigger()
        
        assert alert.trigger_count == 1
        assert alert.last_triggered_at is not None
        
        alert.record_trigger()
        assert alert.trigger_count == 2
    
    def test_to_dict_from_dict(self):
        """Test serialization and deserialization."""
        alert = RiskAlertConfig(
            manager_id="U123456",
            trade_size_threshold=Decimal('100000'),
            loss_percent_threshold=Decimal('5'),
            vix_threshold=Decimal('20'),
            name="Test Alert"
        )
        
        # Convert to dict
        alert_dict = alert.to_dict()
        
        assert alert_dict['manager_id'] == "U123456"
        assert 'alert_id' in alert_dict
        assert alert_dict['name'] == "Test Alert"
        
        # Convert back from dict
        restored_alert = RiskAlertConfig.from_dict(alert_dict)
        
        assert restored_alert.manager_id == alert.manager_id
        assert restored_alert.alert_id == alert.alert_id
        assert restored_alert.trade_size_threshold == alert.trade_size_threshold


@pytest.mark.asyncio
class TestRiskAlertMonitor:
    """Test RiskAlertMonitor service."""
    
    @pytest.fixture
    def mock_db_service(self):
        """Create mock database service."""
        db = Mock(spec=DatabaseService)
        db.is_mock_mode = True
        db.mock_data = {'alerts': {}, 'alert_events': {}}
        db.get_active_alerts = AsyncMock(return_value=[])
        db.save_alert_trigger_event = AsyncMock(return_value=True)
        db.record_alert_trigger = AsyncMock(return_value=True)
        return db
    
    @pytest.fixture
    def mock_notification_service(self):
        """Create mock notification service."""
        notif = Mock()
        notif.send_single_trade_alert = AsyncMock(return_value="notif_123")
        notif.send_risk_alert_summary = AsyncMock(return_value="notif_456")
        return notif
    
    @pytest.fixture
    def mock_market_data_service(self):
        """Create mock market data service."""
        market = Mock()
        
        # Mock VIX quote
        vix_quote = Mock()
        vix_quote.current_price = Decimal('25')
        
        # Mock stock quote
        stock_quote = Mock()
        stock_quote.current_price = Decimal('150')
        
        async def get_quote_mock(symbol):
            if symbol == "^VIX":
                return vix_quote
            else:
                return stock_quote
        
        market.get_quote = get_quote_mock
        return market
    
    @pytest.fixture
    def alert_monitor(self, mock_db_service, mock_notification_service, mock_market_data_service):
        """Create RiskAlertMonitor instance."""
        monitor = RiskAlertMonitor(
            db_service=mock_db_service,
            notification_service=mock_notification_service,
            market_data_service=mock_market_data_service
        )
        return monitor
    
    async def test_check_trade_no_alerts(self, alert_monitor, mock_db_service):
        """Test checking trade when no alerts exist."""
        trade = Trade(
            user_id="U789",
            symbol="AAPL",
            quantity=1000,
            trade_type=TradeType.BUY,
            price=Decimal('150')
        )
        
        # No alerts configured
        mock_db_service.get_active_alerts.return_value = []
        
        # Should not raise exception
        await alert_monitor.check_trade_against_alerts(trade)
        
        # No notifications should be sent
        assert alert_monitor.notifications.send_single_trade_alert.call_count == 0
    
    async def test_check_trade_with_matching_alert(self, alert_monitor, mock_db_service):
        """Test checking trade that matches alert criteria."""
        trade = Trade(
            user_id="U789",
            symbol="AAPL",
            quantity=1000,
            trade_type=TradeType.BUY,
            price=Decimal('150')
        )
        
        # Configure matching alert
        alert = RiskAlertConfig(
            manager_id="U123",
            trade_size_threshold=Decimal('100000'),  # Trade is $150k
            loss_percent_threshold=Decimal('1'),  # Any loss
            vix_threshold=Decimal('20'),  # VIX is 25
            notify_on_new=True
        )
        
        mock_db_service.get_active_alerts.return_value = [alert]
        
        # Check trade
        await alert_monitor.check_trade_against_alerts(trade)
        
        # Notification should be sent
        assert alert_monitor.notifications.send_single_trade_alert.call_count == 1
        
        # Trigger should be recorded
        assert mock_db_service.record_alert_trigger.call_count == 1
        assert mock_db_service.save_alert_trigger_event.call_count == 1
    
    async def test_check_trade_with_non_matching_alert(self, alert_monitor, mock_db_service):
        """Test checking trade that doesn't match alert criteria."""
        trade = Trade(
            user_id="U789",
            symbol="AAPL",
            quantity=100,  # Only $15k
            trade_type=TradeType.BUY,
            price=Decimal('150')
        )
        
        # Configure non-matching alert (threshold too high)
        alert = RiskAlertConfig(
            manager_id="U123",
            trade_size_threshold=Decimal('500000'),  # Trade is only $15k
            loss_percent_threshold=Decimal('1'),
            vix_threshold=Decimal('20'),
            notify_on_new=True
        )
        
        mock_db_service.get_active_alerts.return_value = [alert]
        
        # Check trade
        await alert_monitor.check_trade_against_alerts(trade)
        
        # No notification should be sent
        assert alert_monitor.notifications.send_single_trade_alert.call_count == 0
    
    async def test_calculate_loss_percent_buy(self, alert_monitor):
        """Test loss calculation for BUY trades."""
        # Buy at 100, current price 90 = 10% loss
        loss = alert_monitor._calculate_loss_percent(
            Decimal('100'),
            Decimal('90'),
            TradeType.BUY
        )
        assert loss == Decimal('10')
        
        # Buy at 100, current price 110 = -10% (profit)
        loss = alert_monitor._calculate_loss_percent(
            Decimal('100'),
            Decimal('110'),
            TradeType.BUY
        )
        assert loss == Decimal('-10')
    
    async def test_calculate_loss_percent_sell(self, alert_monitor):
        """Test loss calculation for SELL trades."""
        # Sell at 100, current price 110 = 10% loss
        loss = alert_monitor._calculate_loss_percent(
            Decimal('100'),
            Decimal('110'),
            TradeType.SELL
        )
        assert loss == Decimal('10')
        
        # Sell at 100, current price 90 = -10% (profit)
        loss = alert_monitor._calculate_loss_percent(
            Decimal('100'),
            Decimal('90'),
            TradeType.SELL
        )
        assert loss == Decimal('-10')
    
    async def test_vix_caching(self, alert_monitor):
        """Test VIX data caching."""
        # First call should fetch VIX
        vix1 = await alert_monitor._get_current_vix()
        assert vix1 == Decimal('25')
        
        # Second call should use cache
        vix2 = await alert_monitor._get_current_vix()
        assert vix2 == Decimal('25')
        
        # Cache should be populated
        assert alert_monitor._vix_cache is not None
    
    async def test_matches_criteria(self, alert_monitor):
        """Test criteria matching logic."""
        alert = RiskAlertConfig(
            manager_id="U123",
            trade_size_threshold=Decimal('100000'),
            loss_percent_threshold=Decimal('5'),
            vix_threshold=Decimal('20')
        )
        
        # All criteria met
        assert alert_monitor._matches_criteria(
            Decimal('150000'),  # Size OK
            Decimal('7'),  # Loss OK
            Decimal('25'),  # VIX OK
            alert
        ) == True
        
        # Trade size too small
        assert alert_monitor._matches_criteria(
            Decimal('50000'),  # Size too small
            Decimal('7'),
            Decimal('25'),
            alert
        ) == False
        
        # Loss too small
        assert alert_monitor._matches_criteria(
            Decimal('150000'),
            Decimal('3'),  # Loss too small
            Decimal('25'),
            alert
        ) == False
        
        # VIX too low
        assert alert_monitor._matches_criteria(
            Decimal('150000'),
            Decimal('7'),
            Decimal('15'),  # VIX too low
            alert
        ) == False


def test_integration_import():
    """Test that all modules can be imported."""
    try:
        from models.risk_alert import RiskAlertConfig
        from services.alert_monitor import RiskAlertMonitor
        from ui.risk_alert_widget import create_risk_alert_modal
        from listeners.risk_alert_handlers import register_risk_alert_handlers
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

