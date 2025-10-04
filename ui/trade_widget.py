"""
Comprehensive trade widget UI components for Jain Global Slack Trading Bot.

This module provides sophisticated Block Kit modal generation for trade input,
dynamic form validation, real-time market data display, and risk analysis integration.
It implements role-based UI customization, high-risk confirmation workflows, and
comprehensive error handling with user guidance.

The TradeWidget class creates responsive, accessible interfaces that adapt to user
roles and provide rich trading experiences within Slack's modal framework.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import json

from models.trade import Trade, TradeType, RiskLevel
from models.user import User, UserRole, Permission
from services.market_data import MarketQuote, MarketStatus, DataQuality
from services.risk_analysis import RiskAnalysis, RiskFactor, RiskCategory
from utils.formatters import format_currency, format_percentage, format_number
from utils.validators import validate_symbol, validate_quantity, validate_price

# Configure logging
logger = logging.getLogger(__name__)


class WidgetState(Enum):
    """Widget state enumeration for UI flow control."""
    INITIAL = "initial"
    LOADING_MARKET_DATA = "loading_market_data"
    MARKET_DATA_LOADED = "market_data_loaded"
    ANALYZING_RISK = "analyzing_risk"
    RISK_ANALYSIS_COMPLETE = "risk_analysis_complete"
    HIGH_RISK_CONFIRMATION = "high_risk_confirmation"
    READY_TO_SUBMIT = "ready_to_submit"
    SUBMITTING = "submitting"
    ERROR = "error"


class UITheme(Enum):
    """UI theme options for different contexts."""
    STANDARD = "standard"
    HIGH_RISK = "high_risk"
    CRITICAL_RISK = "critical_risk"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class WidgetContext:
    """Context information for widget rendering."""
    user: User
    channel_id: str
    trigger_id: str
    state: WidgetState = WidgetState.INITIAL
    theme: UITheme = UITheme.STANDARD
    
    # Trade data
    symbol: Optional[str] = None
    quantity: Optional[int] = None
    trade_type: Optional[TradeType] = None
    price: Optional[Decimal] = None
    
    # Market data
    market_quote: Optional[MarketQuote] = None
    
    # Risk analysis
    risk_analysis: Optional[RiskAnalysis] = None
    
    # UI state
    errors: Dict[str, str] = None
    warnings: List[str] = None
    confirmation_required: bool = False
    confirmation_text: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.errors is None:
            self.errors = {}
        if self.warnings is None:
            self.warnings = []


class TradeWidget:
    """
    Comprehensive trade widget UI component generator.
    
    Creates sophisticated Block Kit modals for trade input with dynamic validation,
    real-time market data integration, risk analysis display, and role-based
    customization. Handles complex UI flows including high-risk confirmations
    and error recovery.
    """
    
    def __init__(self):
        """Initialize trade widget with configuration and styling."""
        self.logger = logging.getLogger(__name__)
        
        # UI configuration
        self.max_modal_height = 3000  # Slack modal height limit
        self.animation_enabled = True
        self.accessibility_enabled = True
        
        # Color schemes for different themes
        self.color_schemes = {
            UITheme.STANDARD: {
                'primary': '#1264a3',
                'secondary': '#666666',
                'success': '#2eb886',
                'warning': '#e01e5a',
                'danger': '#e01e5a',
                'background': '#ffffff'
            },
            UITheme.HIGH_RISK: {
                'primary': '#e01e5a',
                'secondary': '#666666',
                'success': '#2eb886',
                'warning': '#ff8c00',
                'danger': '#dc3545',
                'background': '#fff5f5'
            },
            UITheme.CRITICAL_RISK: {
                'primary': '#dc3545',
                'secondary': '#666666',
                'success': '#2eb886',
                'warning': '#ff8c00',
                'danger': '#8b0000',
                'background': '#ffe6e6'
            }
        }
        
        # Role-based UI customizations
        self.role_customizations = {
            UserRole.RESEARCH_ANALYST: {
                'show_advanced_analytics': True,
                'show_research_links': True,
                'default_confirmation': True,
                'risk_analysis_detail': 'comprehensive'
            },
            UserRole.EXECUTION_TRADER: {
                'show_execution_options': True,
                'show_order_types': True,
                'default_confirmation': False,
                'risk_analysis_detail': 'summary'
            },
            UserRole.PORTFOLIO_MANAGER: {
                'show_portfolio_impact': True,
                'show_approval_options': True,
                'default_confirmation': False,
                'risk_analysis_detail': 'comprehensive'
            }
        }
        
        self.logger.info("TradeWidget initialized with role-based customizations")
    
    def create_trade_modal(self, context: WidgetContext) -> Dict[str, Any]:
        """
        Create comprehensive trade modal based on current context and state.
        
        Args:
            context: Widget context with user, state, and data
            
        Returns:
            Slack Block Kit modal JSON
        """
        try:
            # Determine modal configuration based on state and theme
            modal_config = self._get_modal_config(context)
            
            # Build modal structure
            modal = {
                "type": "modal",
                "callback_id": "trade_modal",
                "title": {
                    "type": "plain_text",
                    "text": modal_config['title']
                },
                "blocks": self._build_modal_blocks(context),
                "close": {
                    "type": "plain_text",
                    "text": "Cancel"
                },
                "private_metadata": json.dumps({
                    "user_id": context.user.user_id,
                    "channel_id": context.channel_id,
                    "state": context.state.value,
                    "theme": context.theme.value,
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
            
            # Add submit button if appropriate
            if self._should_show_submit_button(context):
                modal["submit"] = {
                    "type": "plain_text",
                    "text": modal_config['submit_text']
                }
            
            # Add notification text for accessibility
            if self.accessibility_enabled:
                modal["notify_on_close"] = True
            
            self.logger.info("Trade modal created",
                           user_id=context.user.user_id,
                           state=context.state.value,
                           theme=context.theme.value,
                           blocks_count=len(modal["blocks"]))
            
            return modal
            
        except Exception as e:
            self.logger.error("Failed to create trade modal", error=str(e))
            return self._create_error_modal(str(e))
    
    def update_modal_with_market_data(
        self, 
        context: WidgetContext, 
        market_quote: MarketQuote
    ) -> Dict[str, Any]:
        """
        Update modal with real-time market data.
        
        Args:
            context: Current widget context
            market_quote: Market data to display
            
        Returns:
            Updated modal JSON
        """
        try:
            # Update context with market data
            context.market_quote = market_quote
            context.state = WidgetState.MARKET_DATA_LOADED
            
            # Auto-populate price if not set
            if context.price is None:
                context.price = market_quote.current_price
            
            # Create updated modal
            return self.create_trade_modal(context)
            
        except Exception as e:
            self.logger.error("Failed to update modal with market data", error=str(e))
            context.state = WidgetState.ERROR
            context.errors['market_data'] = f"Failed to load market data: {str(e)}"
            return self.create_trade_modal(context)
    
    def update_modal_with_risk_analysis(
        self, 
        context: WidgetContext, 
        risk_analysis: RiskAnalysis
    ) -> Dict[str, Any]:
        """
        Update modal with risk analysis results.
        
        Args:
            context: Current widget context
            risk_analysis: Risk analysis results
            
        Returns:
            Updated modal JSON
        """
        try:
            # Update context with risk analysis
            context.risk_analysis = risk_analysis
            context.state = WidgetState.RISK_ANALYSIS_COMPLETE
            
            # Determine if high-risk confirmation is needed
            if risk_analysis.is_high_risk:
                context.confirmation_required = True
                context.state = WidgetState.HIGH_RISK_CONFIRMATION
                context.theme = UITheme.HIGH_RISK if risk_analysis.overall_risk_level == RiskLevel.HIGH else UITheme.CRITICAL_RISK
            
            # Add risk-based warnings
            if risk_analysis.regulatory_flags:
                context.warnings.extend([f"Regulatory: {flag}" for flag in risk_analysis.regulatory_flags])
            
            # Create updated modal
            return self.create_trade_modal(context)
            
        except Exception as e:
            self.logger.error("Failed to update modal with risk analysis", error=str(e))
            context.state = WidgetState.ERROR
            context.errors['risk_analysis'] = f"Risk analysis failed: {str(e)}"
            return self.create_trade_modal(context)
    
    def create_confirmation_modal(self, context: WidgetContext) -> Dict[str, Any]:
        """
        Create high-risk trade confirmation modal.
        
        Args:
            context: Widget context with risk analysis
            
        Returns:
            Confirmation modal JSON
        """
        try:
            if not context.risk_analysis or not context.risk_analysis.is_high_risk:
                raise ValueError("Confirmation modal requires high-risk analysis")
            
            modal = {
                "type": "modal",
                "callback_id": "trade_confirmation_modal",
                "title": {
                    "type": "plain_text",
                    "text": "⚠️ High-Risk Trade Confirmation"
                },
                "blocks": self._build_confirmation_blocks(context),
                "submit": {
                    "type": "plain_text",
                    "text": "Confirm Trade"
                },
                "close": {
                    "type": "plain_text",
                    "text": "Cancel"
                },
                "private_metadata": json.dumps({
                    "user_id": context.user.user_id,
                    "channel_id": context.channel_id,
                    "trade_data": {
                        "symbol": context.symbol,
                        "quantity": context.quantity,
                        "trade_type": context.trade_type.value if context.trade_type else None,
                        "price": float(context.price) if context.price else None
                    },
                    "risk_analysis_id": context.risk_analysis.trade_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
            
            self.logger.info("Confirmation modal created",
                           user_id=context.user.user_id,
                           risk_level=context.risk_analysis.overall_risk_level.value)
            
            return modal
            
        except Exception as e:
            self.logger.error("Failed to create confirmation modal", error=str(e))
            return self._create_error_modal(str(e))
    
    def _get_modal_config(self, context: WidgetContext) -> Dict[str, str]:
        """Get modal configuration based on state and theme."""
        base_config = {
            'title': 'Execute Trade',
            'submit_text': 'Execute Trade'
        }
        
        if context.state == WidgetState.LOADING_MARKET_DATA:
            base_config['title'] = 'Loading Market Data...'
            base_config['submit_text'] = 'Please Wait'
        elif context.state == WidgetState.ANALYZING_RISK:
            base_config['title'] = 'Analyzing Risk...'
            base_config['submit_text'] = 'Please Wait'
        elif context.state == WidgetState.HIGH_RISK_CONFIRMATION:
            base_config['title'] = '⚠️ High-Risk Trade'
            base_config['submit_text'] = 'Confirm High-Risk Trade'
        elif context.state == WidgetState.ERROR:
            base_config['title'] = '❌ Trade Error'
            base_config['submit_text'] = 'Retry'
        
        return base_config
    
    def _build_modal_blocks(self, context: WidgetContext) -> List[Dict[str, Any]]:
        """Build modal blocks based on context and state."""
        blocks = []
        
        # Add header section
        blocks.extend(self._build_header_section(context))
        
        # Add trade input section
        blocks.extend(self._build_trade_input_section(context))
        
        # Add market data section if available
        if context.market_quote:
            blocks.extend(self._build_market_data_section(context))
        
        # Add risk analysis section if available
        if context.risk_analysis:
            blocks.extend(self._build_risk_analysis_section(context))
        
        # Add confirmation section if required
        if context.confirmation_required:
            blocks.extend(self._build_confirmation_section(context))
        
        # Add error section if errors exist
        if context.errors:
            blocks.extend(self._build_error_section(context))
        
        # Add warnings section if warnings exist
        if context.warnings:
            blocks.extend(self._build_warnings_section(context))
        
        # Add footer section
        blocks.extend(self._build_footer_section(context))
        
        return blocks
    
    def _build_header_section(self, context: WidgetContext) -> List[Dict[str, Any]]:
        """Build header section with user info and role-specific content."""
        blocks = []
        
        # Welcome message with role-specific customization
        role_customization = self.role_customizations.get(context.user.role, {})
        
        if context.user.role == UserRole.RESEARCH_ANALYST:
            header_text = f"*Research Trade Analysis* for {context.user.profile.display_name}"
            description = "Analyze potential trades with comprehensive risk assessment and research integration."
        elif context.user.role == UserRole.EXECUTION_TRADER:
            header_text = f"*Trade Execution* for {context.user.profile.display_name}"
            description = "Execute trades with real-time market data and risk validation."
        elif context.user.role == UserRole.PORTFOLIO_MANAGER:
            header_text = f"*Portfolio Management* for {context.user.profile.display_name}"
            description = "Manage portfolio positions with advanced risk analysis and approval workflows."
        else:
            header_text = f"*Trade Interface* for {context.user.profile.display_name}"
            description = "Execute trades with comprehensive risk management."
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{header_text}\n{description}"
            }
        })
        
        # Add divider
        blocks.append({"type": "divider"})
        
        return blocks
    
    def _build_trade_input_section(self, context: WidgetContext) -> List[Dict[str, Any]]:
        """Build trade input form section."""
        blocks = []
        
        # Symbol input
        symbol_block = {
            "type": "input",
            "block_id": "symbol_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "symbol",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Enter stock symbol (e.g., AAPL, MSFT)"
                },
                "focus_on_load": True
            },
            "label": {
                "type": "plain_text",
                "text": "Stock Symbol"
            }
        }
        
        # Pre-populate if available
        if context.symbol:
            symbol_block["element"]["initial_value"] = context.symbol
        
        # Add error styling if symbol error exists
        if 'symbol' in context.errors:
            symbol_block["element"]["placeholder"]["text"] = f"Error: {context.errors['symbol']}"
        
        blocks.append(symbol_block)
        
        # Trade type selection
        trade_type_options = [
            {
                "text": {
                    "type": "plain_text",
                    "text": "Buy"
                },
                "value": "buy"
            },
            {
                "text": {
                    "type": "plain_text",
                    "text": "Sell"
                },
                "value": "sell"
            }
        ]
        
        trade_type_block = {
            "type": "input",
            "block_id": "trade_type_input",
            "element": {
                "type": "radio_buttons",
                "action_id": "trade_type",
                "options": trade_type_options
            },
            "label": {
                "type": "plain_text",
                "text": "Trade Type"
            }
        }
        
        # Pre-select if available
        if context.trade_type:
            for option in trade_type_options:
                if option["value"] == context.trade_type.value:
                    trade_type_block["element"]["initial_option"] = option
                    break
        
        blocks.append(trade_type_block)
        
        # Quantity and price inputs (side by side)
        quantity_element = {
            "type": "plain_text_input",
            "action_id": "quantity",
            "placeholder": {
                "type": "plain_text",
                "text": "Number of shares"
            }
        }
        
        if context.quantity:
            quantity_element["initial_value"] = str(context.quantity)
        
        if 'quantity' in context.errors:
            quantity_element["placeholder"]["text"] = f"Error: {context.errors['quantity']}"
        
        price_element = {
            "type": "plain_text_input",
            "action_id": "price",
            "placeholder": {
                "type": "plain_text",
                "text": "Price per share ($)"
            }
        }
        
        if context.price:
            price_element["initial_value"] = str(context.price)
        
        if 'price' in context.errors:
            price_element["placeholder"]["text"] = f"Error: {context.errors['price']}"
        
        # Create side-by-side layout
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": "*Quantity*"
                },
                {
                    "type": "mrkdwn",
                    "text": "*Price per Share*"
                }
            ]
        })
        
        blocks.append({
            "type": "input",
            "block_id": "quantity_input",
            "element": quantity_element,
            "label": {
                "type": "plain_text",
                "text": "Quantity"
            }
        })
        
        blocks.append({
            "type": "input",
            "block_id": "price_input",
            "element": price_element,
            "label": {
                "type": "plain_text",
                "text": "Price"
            }
        })
        
        # Add action buttons
        action_elements = []
        
        # Market data button
        action_elements.append({
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "📊 Get Market Data"
            },
            "action_id": "get_market_data",
            "style": "primary" if not context.market_quote else None
        })
        
        # Risk analysis button (only if market data is available)
        if context.market_quote:
            action_elements.append({
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "🔍 Analyze Risk"
                },
                "action_id": "analyze_risk",
                "style": "primary" if not context.risk_analysis else None
            })
        
        if action_elements:
            blocks.append({
                "type": "actions",
                "block_id": "trade_actions",
                "elements": action_elements
            })
        
        return blocks
    
    def _build_market_data_section(self, context: WidgetContext) -> List[Dict[str, Any]]:
        """Build market data display section."""
        blocks = []
        quote = context.market_quote
        
        if not quote:
            return blocks
        
        # Market data header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*📊 Market Data for {quote.symbol}*"
            }
        })
        
        # Price information
        price_change_emoji = "📈" if quote.price_change and quote.price_change > 0 else "📉" if quote.price_change and quote.price_change < 0 else "➡️"
        price_change_text = ""
        
        if quote.price_change and quote.price_change_percent:
            price_change_text = f" ({price_change_emoji} {format_currency(quote.price_change)} / {format_percentage(quote.price_change_percent)})"
        
        price_fields = [
            {
                "type": "mrkdwn",
                "text": f"*Current Price:*\n{format_currency(quote.current_price)}{price_change_text}"
            }
        ]
        
        # Add additional price data if available
        if quote.open_price:
            price_fields.append({
                "type": "mrkdwn",
                "text": f"*Open:* {format_currency(quote.open_price)}"
            })
        
        if quote.high_price and quote.low_price:
            price_fields.extend([
                {
                    "type": "mrkdwn",
                    "text": f"*High:* {format_currency(quote.high_price)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Low:* {format_currency(quote.low_price)}"
                }
            ])
        
        blocks.append({
            "type": "section",
            "fields": price_fields
        })
        
        # Market status and data quality
        status_emoji = "🟢" if quote.market_status == MarketStatus.OPEN else "🔴"
        quality_emoji = "⚡" if quote.data_quality == DataQuality.REAL_TIME else "⏰" if quote.data_quality == DataQuality.DELAYED else "⚠️"
        
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"{status_emoji} Market: {quote.market_status.value.title()} | {quality_emoji} Data: {quote.data_quality.value.title()}"
                }
            ]
        })
        
        # Calculate trade value if quantity is available
        if context.quantity and context.price:
            trade_value = abs(context.quantity * context.price)
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*💰 Estimated Trade Value:* {format_currency(trade_value)}"
                }
            })
        
        return blocks
    
    def _build_risk_analysis_section(self, context: WidgetContext) -> List[Dict[str, Any]]:
        """Build risk analysis display section."""
        blocks = []
        analysis = context.risk_analysis
        
        if not analysis:
            return blocks
        
        # Risk analysis header with risk level indicator
        risk_emoji = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡", 
            RiskLevel.HIGH: "🟠",
            RiskLevel.CRITICAL: "🔴"
        }.get(analysis.overall_risk_level, "❓")
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🔍 Risk Analysis* {risk_emoji} *{analysis.overall_risk_level.value.upper()} RISK*"
            }
        })
        
        # Risk score and summary
        risk_score_bar = "█" * int(analysis.overall_risk_score * 10) + "░" * (10 - int(analysis.overall_risk_score * 10))
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Risk Score:*\n{analysis.overall_risk_score:.1%} `{risk_score_bar}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Analysis Time:*\n{analysis.analysis_duration_ms:.0f}ms" if analysis.analysis_duration_ms else "N/A"
                }
            ]
        })
        
        # Analysis summary
        if analysis.analysis_summary:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary:* {analysis.analysis_summary}"
                }
            })
        
        # Portfolio impact
        if analysis.portfolio_impact:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Portfolio Impact:* {analysis.portfolio_impact}"
                }
            })
        
        # Risk factors (show top 3 most significant)
        if analysis.risk_factors:
            high_risk_factors = analysis.get_high_risk_factors()[:3]
            if high_risk_factors:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*🚨 Key Risk Factors:*"
                    }
                })
                
                for factor in high_risk_factors:
                    factor_emoji = {
                        RiskLevel.LOW: "🟢",
                        RiskLevel.MEDIUM: "🟡",
                        RiskLevel.HIGH: "🟠", 
                        RiskLevel.CRITICAL: "🔴"
                    }.get(factor.level, "❓")
                    
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{factor_emoji} *{factor.category.value.title()}:* {factor.description}"
                        }
                    })
        
        # Recommendations
        if analysis.recommendations:
            rec_text = "\n".join([f"• {rec}" for rec in analysis.recommendations[:3]])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*💡 Recommendations:*\n{rec_text}"
                }
            })
        
        return blocks
    
    def _build_confirmation_section(self, context: WidgetContext) -> List[Dict[str, Any]]:
        """Build high-risk confirmation section."""
        blocks = []
        
        if not context.confirmation_required:
            return blocks
        
        # High-risk warning
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "⚠️ *HIGH-RISK TRADE CONFIRMATION REQUIRED*\n\nThis trade has been flagged as high-risk. Please review the analysis above and type `confirm` below to proceed."
            }
        })
        
        # Confirmation input
        blocks.append({
            "type": "input",
            "block_id": "confirmation_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "confirmation_text",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Type 'confirm' to proceed with high-risk trade"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Confirmation"
            }
        })
        
        return blocks
    
    def _build_confirmation_blocks(self, context: WidgetContext) -> List[Dict[str, Any]]:
        """Build blocks for confirmation modal."""
        blocks = []
        analysis = context.risk_analysis
        
        # Warning header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🚨 *HIGH-RISK TRADE DETECTED*\n\nThe following trade requires your explicit confirmation:"
            }
        })
        
        # Trade summary
        trade_type_text = "Buy" if context.trade_type == TradeType.BUY else "Sell"
        trade_value = abs(context.quantity * context.price) if context.quantity and context.price else 0
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Symbol:* {context.symbol}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Action:* {trade_type_text}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Quantity:* {format_number(context.quantity)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Price:* {format_currency(context.price)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Total Value:* {format_currency(trade_value)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Risk Level:* {analysis.overall_risk_level.value.upper()}"
                }
            ]
        })
        
        blocks.append({"type": "divider"})
        
        # Risk factors
        if analysis.risk_factors:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🚨 Risk Factors:*"
                }
            })
            
            for factor in analysis.get_high_risk_factors()[:5]:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• *{factor.category.value.title()}:* {factor.description}"
                    }
                })
        
        blocks.append({"type": "divider"})
        
        # Confirmation requirement
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "⚠️ *By confirming this trade, you acknowledge that you have reviewed the risk analysis and accept responsibility for this high-risk transaction.*"
            }
        })
        
        # Confirmation input
        blocks.append({
            "type": "input",
            "block_id": "final_confirmation",
            "element": {
                "type": "plain_text_input",
                "action_id": "confirmation_text",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Type 'CONFIRM' to proceed"
                }
            },
            "label": {
                "type": "plain_text",
                "text": "Final Confirmation (type CONFIRM)"
            }
        })
        
        return blocks
    
    def _build_error_section(self, context: WidgetContext) -> List[Dict[str, Any]]:
        """Build error display section."""
        blocks = []
        
        if not context.errors:
            return blocks
        
        # Error header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "❌ *Errors Found:*"
            }
        })
        
        # List errors
        for field, error in context.errors.items():
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• *{field.title()}:* {error}"
                }
            })
        
        return blocks
    
    def _build_warnings_section(self, context: WidgetContext) -> List[Dict[str, Any]]:
        """Build warnings display section."""
        blocks = []
        
        if not context.warnings:
            return blocks
        
        # Warnings header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "⚠️ *Warnings:*"
            }
        })
        
        # List warnings
        for warning in context.warnings:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• {warning}"
                }
            })
        
        return blocks
    
    def _build_footer_section(self, context: WidgetContext) -> List[Dict[str, Any]]:
        """Build footer section with additional info and help."""
        blocks = []
        
        # Add divider
        blocks.append({"type": "divider"})
        
        # Footer context
        footer_elements = []
        
        # Timestamp
        footer_elements.append({
            "type": "mrkdwn",
            "text": f"🕐 {datetime.utcnow().strftime('%H:%M:%S UTC')}"
        })
        
        # User role
        footer_elements.append({
            "type": "mrkdwn",
            "text": f"👤 {context.user.role.value.replace('_', ' ').title()}"
        })
        
        # Channel info
        footer_elements.append({
            "type": "mrkdwn",
            "text": f"📍 <#{context.channel_id}>"
        })
        
        blocks.append({
            "type": "context",
            "elements": footer_elements
        })
        
        return blocks
    
    def _should_show_submit_button(self, context: WidgetContext) -> bool:
        """Determine if submit button should be shown."""
        if context.state in [WidgetState.LOADING_MARKET_DATA, WidgetState.ANALYZING_RISK]:
            return False
        
        if context.state == WidgetState.ERROR:
            return True  # Show as retry button
        
        if context.confirmation_required and not context.confirmation_text:
            return False
        
        # Check if all required fields are present
        required_fields = [context.symbol, context.quantity, context.trade_type, context.price]
        return all(field is not None for field in required_fields)
    
    def _create_error_modal(self, error_message: str) -> Dict[str, Any]:
        """Create error modal for critical failures."""
        return {
            "type": "modal",
            "callback_id": "trade_error_modal",
            "title": {
                "type": "plain_text",
                "text": "❌ Trade Error"
            },
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*An error occurred while processing your trade request:*\n\n```{error_message}```\n\nPlease try again or contact support if the problem persists."
                    }
                }
            ],
            "close": {
                "type": "plain_text",
                "text": "Close"
            }
        }
    
    def validate_modal_input(self, form_data: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
        """
        Validate modal form input data.
        
        Args:
            form_data: Form data from modal submission
            
        Returns:
            Tuple of (is_valid, errors_dict)
        """
        errors = {}
        
        try:
            # Extract form values
            symbol = form_data.get('symbol', '').strip().upper()
            quantity_str = form_data.get('quantity', '').strip()
            price_str = form_data.get('price', '').strip()
            trade_type_str = form_data.get('trade_type', '').strip().lower()
            
            # Validate symbol
            if not symbol:
                errors['symbol'] = "Symbol is required"
            else:
                try:
                    validate_symbol(symbol)
                except ValueError as e:
                    errors['symbol'] = str(e)
            
            # Validate quantity
            if not quantity_str:
                errors['quantity'] = "Quantity is required"
            else:
                try:
                    quantity = int(quantity_str)
                    validate_quantity(quantity)
                except ValueError as e:
                    errors['quantity'] = str(e)
            
            # Validate price
            if not price_str:
                errors['price'] = "Price is required"
            else:
                try:
                    price = Decimal(price_str)
                    validate_price(price)
                except (ValueError, InvalidOperation) as e:
                    errors['price'] = "Invalid price format"
            
            # Validate trade type
            if not trade_type_str:
                errors['trade_type'] = "Trade type is required"
            elif trade_type_str not in ['buy', 'sell']:
                errors['trade_type'] = "Trade type must be 'buy' or 'sell'"
            
            is_valid = len(errors) == 0
            
            self.logger.debug("Modal input validation completed",
                            is_valid=is_valid,
                            error_count=len(errors))
            
            return is_valid, errors
            
        except Exception as e:
            self.logger.error("Modal input validation failed", error=str(e))
            return False, {'general': f"Validation error: {str(e)}"}
    
    def extract_trade_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and normalize trade data from form input.
        
        Args:
            form_data: Raw form data
            
        Returns:
            Normalized trade data dictionary
        """
        try:
            return {
                'symbol': form_data.get('symbol', '').strip().upper(),
                'quantity': int(form_data.get('quantity', 0)),
                'price': Decimal(form_data.get('price', '0')),
                'trade_type': TradeType(form_data.get('trade_type', 'buy').lower()),
                'confirmation_text': form_data.get('confirmation_text', '').strip()
            }
        except Exception as e:
            self.logger.error("Failed to extract trade data", error=str(e))
            raise ValueError(f"Invalid trade data: {str(e)}")