"""
Comprehensive portfolio dashboard components for Jain Global Slack Trading Bot.

This module provides sophisticated App Home tab implementation with position summaries,
P&L displays, trade history, and performance metrics. It implements real-time data updates,
interactive charts, drill-down capabilities, and role-specific dashboard views with
customizable layouts and preferences.

The Dashboard class creates rich, data-driven interfaces that provide comprehensive
portfolio insights and analytics within Slack's App Home framework.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import statistics

from models.portfolio import Portfolio, Position, PortfolioStatus
from models.user import User, UserRole, Permission
from models.trade import Trade, TradeStatus, RiskLevel
from services.market_data import MarketQuote, MarketStatus
from utils.formatters import (
    format_currency, format_percentage, format_number, 
    format_datetime, format_date, format_large_number
)

# Configure logging
logger = logging.getLogger(__name__)


class DashboardView(Enum):
    """Dashboard view types for different contexts."""
    OVERVIEW = "overview"
    POSITIONS = "positions"
    PERFORMANCE = "performance"
    TRADES = "trades"
    ANALYTICS = "analytics"
    SETTINGS = "settings"


class TimeFrame(Enum):
    """Time frame options for performance analysis."""
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL_TIME = "all_time"


class SortOption(Enum):
    """Sorting options for position lists."""
    VALUE_DESC = "value_desc"
    VALUE_ASC = "value_asc"
    PNL_DESC = "pnl_desc"
    PNL_ASC = "pnl_asc"
    SYMBOL_ASC = "symbol_asc"
    SYMBOL_DESC = "symbol_desc"


@dataclass
class DashboardContext:
    """Context information for dashboard rendering."""
    user: User
    portfolio: Portfolio
    view: DashboardView = DashboardView.OVERVIEW
    time_frame: TimeFrame = TimeFrame.TODAY
    sort_option: SortOption = SortOption.VALUE_DESC
    
    # Market data
    market_quotes: Dict[str, MarketQuote] = None
    
    # Recent trades
    recent_trades: List[Trade] = None
    
    # Performance data
    performance_data: Dict[str, Any] = None
    
    # UI preferences
    show_charts: bool = True
    show_risk_metrics: bool = True
    compact_view: bool = False
    
    def __post_init__(self):
        """Initialize default values."""
        if self.market_quotes is None:
            self.market_quotes = {}
        if self.recent_trades is None:
            self.recent_trades = []
        if self.performance_data is None:
            self.performance_data = {}


class Dashboard:
    """
    Comprehensive portfolio dashboard component generator.
    
    Creates sophisticated App Home tab implementations with position summaries,
    P&L displays, trade history, performance metrics, and interactive analytics.
    Provides role-specific customization and real-time data integration.
    """
    
    def __init__(self):
        """Initialize dashboard with configuration and styling."""
        self.logger = logging.getLogger(__name__)
        
        # UI configuration
        self.max_positions_display = 20
        self.max_trades_display = 10
        self.chart_enabled = True
        
        # Color schemes for different metrics
        self.color_schemes = {
            'positive': '#2eb886',
            'negative': '#e01e5a', 
            'neutral': '#666666',
            'warning': '#ff8c00',
            'info': '#1264a3'
        }
        
        # Role-based dashboard customizations
        self.role_customizations = {
            UserRole.RESEARCH_ANALYST: {
                'default_view': DashboardView.ANALYTICS,
                'show_research_tools': True,
                'show_detailed_metrics': True,
                'enable_export': True
            },
            UserRole.EXECUTION_TRADER: {
                'default_view': DashboardView.POSITIONS,
                'show_execution_tools': True,
                'show_order_status': True,
                'enable_quick_trade': True
            },
            UserRole.PORTFOLIO_MANAGER: {
                'default_view': DashboardView.OVERVIEW,
                'show_risk_management': True,
                'show_allocation_tools': True,
                'enable_rebalancing': True
            }
        }
        
        self.logger.info("Dashboard initialized with role-based customizations")
    
    def create_app_home_view(self, context: DashboardContext) -> Dict[str, Any]:
        """
        Create comprehensive App Home tab view.
        
        Args:
            context: Dashboard context with user, portfolio, and preferences
            
        Returns:
            Slack App Home view JSON
        """
        try:
            # Build view based on current context
            blocks = []
            
            # Add header section
            blocks.extend(self._build_header_section(context))
            
            # Add navigation section
            blocks.extend(self._build_navigation_section(context))
            
            # Add main content based on view
            if context.view == DashboardView.OVERVIEW:
                blocks.extend(self._build_overview_section(context))
            elif context.view == DashboardView.POSITIONS:
                blocks.extend(self._build_positions_section(context))
            elif context.view == DashboardView.PERFORMANCE:
                blocks.extend(self._build_performance_section(context))
            elif context.view == DashboardView.TRADES:
                blocks.extend(self._build_trades_section(context))
            elif context.view == DashboardView.ANALYTICS:
                blocks.extend(self._build_analytics_section(context))
            elif context.view == DashboardView.SETTINGS:
                blocks.extend(self._build_settings_section(context))
            
            # Add footer section
            blocks.extend(self._build_footer_section(context))
            
            # Create App Home view
            app_home_view = {
                "type": "home",
                "blocks": blocks,
                "private_metadata": json.dumps({
                    "user_id": context.user.user_id,
                    "portfolio_id": context.portfolio.portfolio_id,
                    "view": context.view.value,
                    "time_frame": context.time_frame.value,
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
            
            self.logger.info("App Home view created",
                           user_id=context.user.user_id,
                           view=context.view.value,
                           blocks_count=len(blocks))
            
            return app_home_view
            
        except Exception as e:
            self.logger.error("Failed to create App Home view", error=str(e))
            return self._create_error_view(str(e))
    
    def _build_header_section(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build header section with portfolio summary."""
        blocks = []
        portfolio = context.portfolio
        
        # Portfolio title and status
        status_emoji = {
            PortfolioStatus.ACTIVE: "🟢",
            PortfolioStatus.INACTIVE: "🔴",
            PortfolioStatus.FROZEN: "🟡",
            PortfolioStatus.LIQUIDATING: "🟠"
        }.get(portfolio.status, "❓")
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📊 {portfolio.name}* {status_emoji}\n_{context.user.profile.display_name} • {context.user.role.value.replace('_', ' ').title()}_"
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "⚡ Quick Trade"
                },
                "action_id": "quick_trade_button",
                "style": "primary"
            }
        })
        
        # Key metrics summary
        performance = portfolio.get_performance_summary()
        pnl_color = self.color_schemes['positive'] if portfolio.total_pnl >= 0 else self.color_schemes['negative']
        day_change_color = self.color_schemes['positive'] if portfolio.day_change >= 0 else self.color_schemes['negative']
        
        pnl_emoji = "📈" if portfolio.total_pnl >= 0 else "📉"
        day_emoji = "⬆️" if portfolio.day_change >= 0 else "⬇️"
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Total Value*\n{format_currency(portfolio.total_value)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Cash Balance*\n{format_currency(portfolio.cash_balance)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Total P&L* {pnl_emoji}\n{format_currency(portfolio.total_pnl)} ({format_percentage(performance['total_pnl_pct'])})"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Day Change* {day_emoji}\n{format_currency(portfolio.day_change)} ({format_percentage(portfolio.day_change_percent)})"
                }
            ]
        })
        
        # Market status and last update
        market_status = "🟢 Open" if any(
            quote.market_status == MarketStatus.OPEN 
            for quote in context.market_quotes.values()
        ) else "🔴 Closed"
        
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Market: {market_status} | Last Updated: {format_datetime(portfolio.last_updated)} | Positions: {len(portfolio.get_active_positions())}"
                }
            ]
        })
        
        blocks.append({"type": "divider"})
        
        return blocks   
 
    def _build_navigation_section(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build navigation section with view selection."""
        blocks = []
        
        # Navigation buttons
        nav_buttons = []
        
        # Define available views based on user role
        role_customization = self.role_customizations.get(context.user.role, {})
        
        view_configs = [
            (DashboardView.OVERVIEW, "📊 Overview", "primary" if context.view == DashboardView.OVERVIEW else None),
            (DashboardView.POSITIONS, "💼 Positions", "primary" if context.view == DashboardView.POSITIONS else None),
            (DashboardView.PERFORMANCE, "📈 Performance", "primary" if context.view == DashboardView.PERFORMANCE else None),
            (DashboardView.TRADES, "📋 Trades", "primary" if context.view == DashboardView.TRADES else None),
        ]
        
        # Add analytics view for research analysts and portfolio managers
        if context.user.role in [UserRole.RESEARCH_ANALYST, UserRole.PORTFOLIO_MANAGER]:
            view_configs.append((DashboardView.ANALYTICS, "🔍 Analytics", "primary" if context.view == DashboardView.ANALYTICS else None))
        
        # Add settings view
        view_configs.append((DashboardView.SETTINGS, "⚙️ Settings", "primary" if context.view == DashboardView.SETTINGS else None))
        
        for view, text, style in view_configs:
            nav_buttons.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": text
                },
                "action_id": f"dashboard_view_{view.value}",
                "style": style
            })
        
        # Split buttons into rows (max 5 per row)
        button_rows = [nav_buttons[i:i+5] for i in range(0, len(nav_buttons), 5)]
        
        for row in button_rows:
            blocks.append({
                "type": "actions",
                "elements": row
            })
        
        blocks.append({"type": "divider"})
        
        return blocks
    
    def _build_overview_section(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build overview section with key metrics and summaries."""
        blocks = []
        portfolio = context.portfolio
        
        # Section header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📊 Portfolio Overview*"
            }
        })
        
        # Portfolio allocation chart (text-based)
        if portfolio.get_active_positions():
            blocks.extend(self._build_allocation_chart(context))
        
        # Top positions summary
        top_positions = portfolio.get_top_positions(5)
        if top_positions:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🏆 Top 5 Positions*"
                }
            })
            
            for i, position in enumerate(top_positions, 1):
                pnl_emoji = "📈" if position.get_total_pnl() >= 0 else "📉"
                allocation = portfolio.get_portfolio_allocation().get(position.symbol, Decimal('0'))
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{i}. {position.symbol}* ({format_percentage(allocation)})\n{format_currency(position.current_value)} • {pnl_emoji} {format_currency(position.get_total_pnl())} ({format_percentage(position.get_pnl_percentage())})"
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View"
                        },
                        "action_id": f"view_position_{position.symbol}",
                        "value": position.symbol
                    }
                })
        
        # Recent activity
        if context.recent_trades:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*📋 Recent Activity*"
                }
            })
            
            for trade in context.recent_trades[:3]:
                trade_emoji = "🟢" if trade.trade_type.value == "buy" else "🔴"
                status_emoji = {
                    TradeStatus.EXECUTED: "✅",
                    TradeStatus.PENDING: "⏳",
                    TradeStatus.FAILED: "❌"
                }.get(trade.status, "❓")
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{trade_emoji} *{trade.trade_type.value.upper()}* {format_number(trade.quantity)} {trade.symbol} @ {format_currency(trade.price)} {status_emoji}\n_{format_datetime(trade.timestamp)}_"
                    }
                })
        
        # Risk metrics summary
        if context.show_risk_metrics:
            blocks.extend(self._build_risk_metrics_summary(context))
        
        return blocks
    
    def _build_positions_section(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build detailed positions section."""
        blocks = []
        portfolio = context.portfolio
        
        # Section header with controls
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*💼 Portfolio Positions*"
            },
            "accessory": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Sort by..."
                },
                "action_id": "positions_sort",
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "Value (High to Low)"},
                        "value": "value_desc"
                    },
                    {
                        "text": {"type": "plain_text", "text": "Value (Low to High)"},
                        "value": "value_asc"
                    },
                    {
                        "text": {"type": "plain_text", "text": "P&L (High to Low)"},
                        "value": "pnl_desc"
                    },
                    {
                        "text": {"type": "plain_text", "text": "P&L (Low to High)"},
                        "value": "pnl_asc"
                    },
                    {
                        "text": {"type": "plain_text", "text": "Symbol (A-Z)"},
                        "value": "symbol_asc"
                    }
                ]
            }
        })
        
        # Get sorted positions
        positions = self._sort_positions(portfolio.get_active_positions(), context.sort_option)
        
        if not positions:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "📭 *No active positions*\n\nStart trading to see your positions here."
                }
            })
            return blocks
        
        # Position summary stats
        total_positions = len(positions)
        profitable_positions = sum(1 for pos in positions if pos.is_profitable())
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Total Positions:* {total_positions}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Profitable:* {profitable_positions} ({format_percentage(profitable_positions/total_positions*100)})"
                }
            ]
        })
        
        blocks.append({"type": "divider"})
        
        # Display positions
        for position in positions[:self.max_positions_display]:
            blocks.extend(self._build_position_card(position, context))
        
        # Show more button if there are additional positions
        if len(positions) > self.max_positions_display:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"_Showing {self.max_positions_display} of {len(positions)} positions_"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Show All"
                    },
                    "action_id": "show_all_positions"
                }
            })
        
        return blocks
    
    def _build_performance_section(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build performance analysis section."""
        blocks = []
        portfolio = context.portfolio
        
        # Section header with time frame selector
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📈 Performance Analysis*"
            },
            "accessory": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Time Frame"
                },
                "action_id": "performance_timeframe",
                "initial_option": {
                    "text": {"type": "plain_text", "text": context.time_frame.value.title()},
                    "value": context.time_frame.value
                },
                "options": [
                    {"text": {"type": "plain_text", "text": "Today"}, "value": "today"},
                    {"text": {"type": "plain_text", "text": "Week"}, "value": "week"},
                    {"text": {"type": "plain_text", "text": "Month"}, "value": "month"},
                    {"text": {"type": "plain_text", "text": "Quarter"}, "value": "quarter"},
                    {"text": {"type": "plain_text", "text": "Year"}, "value": "year"},
                    {"text": {"type": "plain_text", "text": "All Time"}, "value": "all_time"}
                ]
            }
        })
        
        # Performance metrics
        performance = portfolio.get_performance_summary()
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Total Return*\n{format_currency(portfolio.total_pnl)} ({format_percentage(performance['total_pnl_pct'])})"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Days Active*\n{performance['days_active']} days"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Largest Position*\n{format_currency(performance['largest_position'])}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Portfolio Value*\n{format_currency(portfolio.total_value)}"
                }
            ]
        })
        
        # Performance chart (text-based visualization)
        if portfolio.performance_history:
            blocks.extend(self._build_performance_chart(context))
        
        # Best and worst performers
        positions = portfolio.get_active_positions()
        if positions:
            # Sort by P&L percentage
            sorted_by_pnl = sorted(positions, key=lambda p: p.get_pnl_percentage(), reverse=True)
            
            best_performers = sorted_by_pnl[:3]
            worst_performers = sorted_by_pnl[-3:]
            
            blocks.append({"type": "divider"})
            
            # Best performers
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🏆 Best Performers*"
                }
            })
            
            for position in best_performers:
                pnl_pct = position.get_pnl_percentage()
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📈 *{position.symbol}*: {format_currency(position.get_total_pnl())} ({format_percentage(pnl_pct)})"
                    }
                })
            
            # Worst performers (if any are negative)
            if worst_performers and worst_performers[0].get_pnl_percentage() < 0:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*📉 Underperformers*"
                    }
                })
                
                for position in worst_performers:
                    if position.get_pnl_percentage() < 0:
                        pnl_pct = position.get_pnl_percentage()
                        blocks.append({
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"📉 *{position.symbol}*: {format_currency(position.get_total_pnl())} ({format_percentage(pnl_pct)})"
                            }
                        })
        
        return blocks
    
    def _build_trades_section(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build trade history section."""
        blocks = []
        
        # Section header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📋 Trade History*"
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "📊 Export"
                },
                "action_id": "export_trades"
            }
        })
        
        if not context.recent_trades:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "📭 *No recent trades*\n\nYour trade history will appear here once you start trading."
                }
            })
            return blocks
        
        # Trade statistics
        executed_trades = [t for t in context.recent_trades if t.status == TradeStatus.EXECUTED]
        buy_trades = [t for t in executed_trades if t.trade_type.value == "buy"]
        sell_trades = [t for t in executed_trades if t.trade_type.value == "sell"]
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Total Trades:* {len(context.recent_trades)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Executed:* {len(executed_trades)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Buy Orders:* {len(buy_trades)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Sell Orders:* {len(sell_trades)}"
                }
            ]
        })
        
        blocks.append({"type": "divider"})
        
        # Display recent trades
        for trade in context.recent_trades[:self.max_trades_display]:
            blocks.extend(self._build_trade_card(trade, context))
        
        # Show more button if there are additional trades
        if len(context.recent_trades) > self.max_trades_display:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"_Showing {self.max_trades_display} of {len(context.recent_trades)} trades_"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Show All"
                    },
                    "action_id": "show_all_trades"
                }
            })
        
        return blocks    
    d
ef _build_analytics_section(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build advanced analytics section."""
        blocks = []
        portfolio = context.portfolio
        
        # Section header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🔍 Portfolio Analytics*"
            }
        })
        
        # Calculate and display risk metrics
        risk_metrics = portfolio.calculate_portfolio_risk_metrics()
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📊 Risk Metrics*"
            }
        })
        
        risk_fields = []
        
        if 'max_position_weight' in risk_metrics:
            risk_fields.append({
                "type": "mrkdwn",
                "text": f"*Max Position:*\n{format_percentage(risk_metrics['max_position_weight'])}"
            })
        
        if 'portfolio_concentration' in risk_metrics:
            risk_fields.append({
                "type": "mrkdwn",
                "text": f"*Top 5 Concentration:*\n{format_percentage(risk_metrics['portfolio_concentration'])}"
            })
        
        if 'cash_allocation' in risk_metrics:
            risk_fields.append({
                "type": "mrkdwn",
                "text": f"*Cash Allocation:*\n{format_percentage(risk_metrics['cash_allocation'])}"
            })
        
        if 'profitable_positions_pct' in risk_metrics:
            risk_fields.append({
                "type": "mrkdwn",
                "text": f"*Profitable Positions:*\n{format_percentage(risk_metrics['profitable_positions_pct'])}"
            })
        
        if risk_fields:
            blocks.append({
                "type": "section",
                "fields": risk_fields
            })
        
        # Sector allocation (if available)
        blocks.extend(self._build_sector_analysis(context))
        
        # Correlation analysis
        blocks.extend(self._build_correlation_analysis(context))
        
        # Risk recommendations
        blocks.extend(self._build_risk_recommendations(context))
        
        return blocks
    
    def _build_settings_section(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build settings and preferences section."""
        blocks = []
        portfolio = context.portfolio
        
        # Section header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*⚙️ Portfolio Settings*"
            }
        })
        
        # Portfolio settings
        settings = portfolio.settings
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Portfolio Configuration*"
            }
        })
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Risk Tolerance:*\n{settings.get('risk_tolerance', 'medium').title()}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Max Position Size:*\n{settings.get('max_position_size', '10.0')}%"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Auto Rebalance:*\n{'Enabled' if settings.get('auto_rebalance', False) else 'Disabled'}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Benchmark:*\n{portfolio.benchmark_symbol}"
                }
            ]
        })
        
        # User preferences
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Display Preferences*"
            }
        })
        
        # Toggle buttons for preferences
        preference_buttons = [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Charts: {'On' if context.show_charts else 'Off'}"
                },
                "action_id": "toggle_charts",
                "style": "primary" if context.show_charts else None
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": f"🔍 Risk Metrics: {'On' if context.show_risk_metrics else 'Off'}"
                },
                "action_id": "toggle_risk_metrics",
                "style": "primary" if context.show_risk_metrics else None
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": f"📱 Compact View: {'On' if context.compact_view else 'Off'}"
                },
                "action_id": "toggle_compact_view",
                "style": "primary" if context.compact_view else None
            }
        ]
        
        blocks.append({
            "type": "actions",
            "elements": preference_buttons
        })
        
        # Account information
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Account Information*"
            }
        })
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Portfolio ID:*\n`{portfolio.portfolio_id}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Created:*\n{format_date(portfolio.inception_date)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Status:*\n{portfolio.status.value.title()}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*User Role:*\n{context.user.role.value.replace('_', ' ').title()}"
                }
            ]
        })
        
        return blocks
    
    def _build_footer_section(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build footer section with additional info."""
        blocks = []
        
        blocks.append({"type": "divider"})
        
        # Footer context
        footer_elements = [
            {
                "type": "mrkdwn",
                "text": f"🕐 Last Updated: {format_datetime(datetime.utcnow())}"
            },
            {
                "type": "mrkdwn",
                "text": f"👤 {context.user.profile.display_name}"
            },
            {
                "type": "mrkdwn",
                "text": f"📊 Jain Global Trading Bot"
            }
        ]
        
        blocks.append({
            "type": "context",
            "elements": footer_elements
        })
        
        return blocks
    
    def _build_allocation_chart(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build text-based allocation chart."""
        blocks = []
        portfolio = context.portfolio
        
        allocation = portfolio.get_portfolio_allocation()
        if not allocation:
            return blocks
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📊 Portfolio Allocation*"
            }
        })
        
        # Sort by allocation percentage
        sorted_allocation = sorted(allocation.items(), key=lambda x: x[1], reverse=True)
        
        # Create text-based chart
        chart_text = ""
        for symbol, percentage in sorted_allocation[:10]:  # Top 10
            bar_length = int(percentage / 5)  # Scale for display
            bar = "█" * bar_length + "░" * (20 - bar_length)
            chart_text += f"`{bar}` {symbol}: {format_percentage(percentage)}\n"
        
        if chart_text:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": chart_text.strip()
                }
            })
        
        return blocks
    
    def _build_risk_metrics_summary(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build risk metrics summary."""
        blocks = []
        portfolio = context.portfolio
        
        risk_metrics = portfolio.calculate_portfolio_risk_metrics()
        if not risk_metrics:
            return blocks
        
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*⚠️ Risk Summary*"
            }
        })
        
        # Risk level indicators
        risk_indicators = []
        
        # Concentration risk
        max_position = risk_metrics.get('max_position_weight', Decimal('0'))
        if max_position > 15:
            risk_indicators.append("🔴 High concentration risk")
        elif max_position > 10:
            risk_indicators.append("🟡 Moderate concentration risk")
        else:
            risk_indicators.append("🟢 Low concentration risk")
        
        # Cash allocation
        cash_allocation = risk_metrics.get('cash_allocation', Decimal('0'))
        if cash_allocation > 20:
            risk_indicators.append("💰 High cash allocation")
        elif cash_allocation < 5:
            risk_indicators.append("⚠️ Low cash reserves")
        
        if risk_indicators:
            risk_text = "\n".join([f"• {indicator}" for indicator in risk_indicators])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": risk_text
                }
            })
        
        return blocks
    
    def _build_position_card(self, position: Position, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build individual position card."""
        blocks = []
        
        # Position header
        pnl_emoji = "📈" if position.get_total_pnl() >= 0 else "📉"
        position_type_emoji = "🟢" if position.position_type.value == "long" else "🔴"
        
        # Get current market quote if available
        current_quote = context.market_quotes.get(position.symbol)
        price_change_text = ""
        if current_quote and current_quote.price_change_percent:
            change_emoji = "⬆️" if current_quote.price_change_percent > 0 else "⬇️"
            price_change_text = f" {change_emoji} {format_percentage(current_quote.price_change_percent)}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{position_type_emoji} *{position.symbol}* {price_change_text}\n{format_number(position.quantity)} shares @ {format_currency(position.current_price)}"
            },
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Value:*\n{format_currency(position.current_value)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*P&L:* {pnl_emoji}\n{format_currency(position.get_total_pnl())} ({format_percentage(position.get_pnl_percentage())})"
                }
            ],
            "accessory": {
                "type": "overflow",
                "action_id": f"position_actions_{position.symbol}",
                "options": [
                    {
                        "text": {"type": "plain_text", "text": "View Details"},
                        "value": f"view_{position.symbol}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "Trade"},
                        "value": f"trade_{position.symbol}"
                    },
                    {
                        "text": {"type": "plain_text", "text": "Set Alert"},
                        "value": f"alert_{position.symbol}"
                    }
                ]
            }
        })
        
        return blocks
    
    def _build_trade_card(self, trade: Trade, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build individual trade card."""
        blocks = []
        
        # Trade header
        trade_emoji = "🟢" if trade.trade_type.value == "buy" else "🔴"
        status_emoji = {
            TradeStatus.EXECUTED: "✅",
            TradeStatus.PENDING: "⏳",
            TradeStatus.FAILED: "❌",
            TradeStatus.CANCELLED: "🚫"
        }.get(trade.status, "❓")
        
        risk_emoji = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.HIGH: "🟠",
            RiskLevel.CRITICAL: "🔴"
        }.get(trade.risk_level, "")
        
        trade_value = abs(trade.quantity * trade.price)
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{trade_emoji} *{trade.trade_type.value.upper()}* {format_number(trade.quantity)} {trade.symbol} @ {format_currency(trade.price)} {status_emoji}\n{format_currency(trade_value)} • {format_datetime(trade.timestamp)} {risk_emoji}"
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Details"
                },
                "action_id": f"trade_details_{trade.trade_id}",
                "value": trade.trade_id
            }
        })
        
        return blocks
    
    def _build_performance_chart(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build text-based performance chart."""
        blocks = []
        portfolio = context.portfolio
        
        if not portfolio.performance_history:
            return blocks
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📈 Performance Chart (Last 30 Days)*"
            }
        })
        
        # Get last 30 days of data
        recent_history = portfolio.performance_history[-30:]
        if len(recent_history) < 2:
            return blocks
        
        # Create simple text chart
        values = [entry['total_value'] for entry in recent_history]
        min_val, max_val = min(values), max(values)
        
        if max_val == min_val:
            return blocks
        
        chart_text = ""
        for i, entry in enumerate(recent_history[-10:]):  # Last 10 days
            value = entry['total_value']
            normalized = (value - min_val) / (max_val - min_val)
            bar_length = int(normalized * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            date_str = entry['date'][-5:]  # MM-DD
            chart_text += f"`{bar}` {date_str}: {format_currency(value)}\n"
        
        if chart_text:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": chart_text.strip()
                }
            })
        
        return blocks
    
    def _build_sector_analysis(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build sector allocation analysis."""
        blocks = []
        
        # This would require sector data from market data service
        # For now, return placeholder
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🏭 Sector Analysis*\n_Sector allocation data will be available with enhanced market data integration._"
            }
        })
        
        return blocks
    
    def _build_correlation_analysis(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build correlation analysis."""
        blocks = []
        
        # Placeholder for correlation analysis
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*🔗 Correlation Analysis*\n_Position correlation analysis will be available with historical price data._"
            }
        })
        
        return blocks
    
    def _build_risk_recommendations(self, context: DashboardContext) -> List[Dict[str, Any]]:
        """Build risk-based recommendations."""
        blocks = []
        portfolio = context.portfolio
        
        recommendations = []
        risk_metrics = portfolio.calculate_portfolio_risk_metrics()
        
        # Generate recommendations based on risk metrics
        max_position = risk_metrics.get('max_position_weight', Decimal('0'))
        if max_position > 15:
            recommendations.append("Consider reducing your largest position to improve diversification")
        
        cash_allocation = risk_metrics.get('cash_allocation', Decimal('0'))
        if cash_allocation > 25:
            recommendations.append("High cash allocation - consider deploying capital for better returns")
        elif cash_allocation < 5:
            recommendations.append("Low cash reserves - consider maintaining higher cash buffer")
        
        position_count = len(portfolio.get_active_positions())
        if position_count < 5:
            recommendations.append("Consider diversifying across more positions to reduce risk")
        elif position_count > 20:
            recommendations.append("Large number of positions - consider consolidating for better management")
        
        if recommendations:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*💡 Risk Recommendations*"
                }
            })
            
            rec_text = "\n".join([f"• {rec}" for rec in recommendations])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": rec_text
                }
            })
        
        return blocks
    
    def _sort_positions(self, positions: List[Position], sort_option: SortOption) -> List[Position]:
        """Sort positions based on the specified option."""
        if sort_option == SortOption.VALUE_DESC:
            return sorted(positions, key=lambda p: abs(p.current_value), reverse=True)
        elif sort_option == SortOption.VALUE_ASC:
            return sorted(positions, key=lambda p: abs(p.current_value))
        elif sort_option == SortOption.PNL_DESC:
            return sorted(positions, key=lambda p: p.get_total_pnl(), reverse=True)
        elif sort_option == SortOption.PNL_ASC:
            return sorted(positions, key=lambda p: p.get_total_pnl())
        elif sort_option == SortOption.SYMBOL_ASC:
            return sorted(positions, key=lambda p: p.symbol)
        elif sort_option == SortOption.SYMBOL_DESC:
            return sorted(positions, key=lambda p: p.symbol, reverse=True)
        else:
            return positions
    
    def _create_error_view(self, error_message: str) -> Dict[str, Any]:
        """Create error view for critical failures."""
        return {
            "type": "home",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*❌ Dashboard Error*\n\nAn error occurred while loading your dashboard:\n\n```{error_message}```\n\nPlease try refreshing or contact support if the problem persists."
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "🔄 Refresh Dashboard"
                            },
                            "action_id": "refresh_dashboard",
                            "style": "primary"
                        }
                    ]
                }
            ]
        }
    
    def create_position_detail_modal(self, position: Position, market_quote: Optional[MarketQuote] = None) -> Dict[str, Any]:
        """
        Create detailed position modal.
        
        Args:
            position: Position to display
            market_quote: Current market data
            
        Returns:
            Position detail modal JSON
        """
        try:
            blocks = []
            
            # Position header
            pnl_emoji = "📈" if position.get_total_pnl() >= 0 else "📉"
            position_type_emoji = "🟢" if position.position_type.value == "long" else "🔴"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{position_type_emoji} *{position.symbol} Position Details*"
                }
            })
            
            # Position metrics
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Quantity:*\n{format_number(position.quantity)} shares"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Average Cost:*\n{format_currency(position.average_cost)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Current Price:*\n{format_currency(position.current_price)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Current Value:*\n{format_currency(position.current_value)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Total P&L:* {pnl_emoji}\n{format_currency(position.get_total_pnl())}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*P&L %:*\n{format_percentage(position.get_pnl_percentage())}"
                    }
                ]
            })
            
            # Market data if available
            if market_quote:
                blocks.append({"type": "divider"})
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*📊 Current Market Data*"
                    }
                })
                
                price_change_text = ""
                if market_quote.price_change and market_quote.price_change_percent:
                    change_emoji = "📈" if market_quote.price_change > 0 else "📉"
                    price_change_text = f"{change_emoji} {format_currency(market_quote.price_change)} ({format_percentage(market_quote.price_change_percent)})"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Price:* {format_currency(market_quote.current_price)}\n*Change:* {price_change_text}"
                    }
                })
            
            # Position history
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📅 Position History*\n*Opened:* {format_date(position.opened_date)}\n*Holding Period:* {position.get_holding_period_days()} days\n*Trades:* {len(position.trade_history)}"
                }
            })
            
            # Action buttons
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📈 Trade"
                        },
                        "action_id": f"trade_position_{position.symbol}",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔔 Set Alert"
                        },
                        "action_id": f"set_alert_{position.symbol}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📊 Analysis"
                        },
                        "action_id": f"analyze_position_{position.symbol}"
                    }
                ]
            })
            
            return {
                "type": "modal",
                "callback_id": "position_detail_modal",
                "title": {
                    "type": "plain_text",
                    "text": f"{position.symbol} Details"
                },
                "blocks": blocks,
                "close": {
                    "type": "plain_text",
                    "text": "Close"
                }
            }
            
        except Exception as e:
            self.logger.error("Failed to create position detail modal", error=str(e))
            return self._create_error_modal(str(e))
    
    def _create_error_modal(self, error_message: str) -> Dict[str, Any]:
        """Create error modal for critical failures."""
        return {
            "type": "modal",
            "callback_id": "dashboard_error_modal",
            "title": {
                "type": "plain_text",
                "text": "❌ Dashboard Error"
            },
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*An error occurred:*\n\n```{error_message}```\n\nPlease try again or contact support."
                    }
                }
            ],
            "close": {
                "type": "plain_text",
                "text": "Close"
            }
        }