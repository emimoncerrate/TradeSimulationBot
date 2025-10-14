#!/usr/bin/env python3
"""
Demo script for Enhanced /trade Command with Live Market Data

This script demonstrates the enhanced /trade command capabilities including
real-time market data display, interactive controls, and advanced visualization.

Run this script to see example outputs and test the enhanced features.
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

# Mock the enhanced trade command for demonstration
class MockEnhancedTradeDemo:
    """Mock enhanced trade command for demonstration purposes."""
    
    def __init__(self):
        """Initialize demo with sample data."""
        self.sample_quotes = {
            "AAPL": {
                "symbol": "AAPL",
                "current_price": 150.25,
                "open_price": 148.50,
                "high_price": 151.75,
                "low_price": 147.80,
                "previous_close": 149.00,
                "volume": 45_000_000,
                "market_cap": 2_400_000_000_000,
                "pe_ratio": 28.5,
                "price_change": 1.25,
                "price_change_percent": 0.84,
                "market_status": "open",
                "data_quality": "real_time",
                "exchange": "NASDAQ",
                "api_latency_ms": 125.0
            },
            "TSLA": {
                "symbol": "TSLA",
                "current_price": 245.67,
                "open_price": 248.90,
                "high_price": 249.50,
                "low_price": 243.20,
                "previous_close": 247.30,
                "volume": 28_500_000,
                "market_cap": 780_000_000_000,
                "pe_ratio": 65.2,
                "price_change": -1.63,
                "price_change_percent": -0.66,
                "market_status": "open",
                "data_quality": "real_time",
                "exchange": "NASDAQ",
                "api_latency_ms": 98.0
            },
            "MSFT": {
                "symbol": "MSFT",
                "current_price": 378.92,
                "open_price": 376.45,
                "high_price": 380.15,
                "low_price": 375.80,
                "previous_close": 377.50,
                "volume": 22_100_000,
                "market_cap": 2_800_000_000_000,
                "pe_ratio": 32.1,
                "price_change": 1.42,
                "price_change_percent": 0.38,
                "market_status": "open",
                "data_quality": "real_time",
                "exchange": "NASDAQ",
                "api_latency_ms": 87.0
            }
        }
    
    def generate_modal_preview(self, symbol: str) -> Dict[str, Any]:
        """Generate a preview of the enhanced trade modal."""
        if symbol not in self.sample_quotes:
            return {"error": f"Symbol {symbol} not found in demo data"}
        
        quote = self.sample_quotes[symbol]
        
        # Generate modal structure
        modal = {
            "type": "modal",
            "title": "📊 Live Market Data",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*📊 Live Market Data Trading* 🔴 LIVE • Updated {datetime.now().strftime('%H:%M:%S')}"
                    }
                },
                {"type": "divider"},
                {
                    "type": "input",
                    "label": {"type": "plain_text", "text": "Stock Symbol"},
                    "element": {
                        "type": "plain_text_input",
                        "placeholder": {"type": "plain_text", "text": "Enter stock symbol (e.g., AAPL, TSLA, MSFT)"},
                        "initial_value": symbol
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "AAPL"}} if symbol != "AAPL" else {"type": "button", "text": {"type": "plain_text", "text": "AAPL"}, "style": "primary"},
                        {"type": "button", "text": {"type": "plain_text", "text": "TSLA"}} if symbol != "TSLA" else {"type": "button", "text": {"type": "plain_text", "text": "TSLA"}, "style": "primary"},
                        {"type": "button", "text": {"type": "plain_text", "text": "MSFT"}} if symbol != "MSFT" else {"type": "button", "text": {"type": "plain_text", "text": "MSFT"}, "style": "primary"},
                        {"type": "button", "text": {"type": "plain_text", "text": "GOOGL"}},
                        {"type": "button", "text": {"type": "plain_text", "text": "🔄 Refresh"}, "style": "primary"}
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*📈 {quote['symbol']} ({quote['exchange']}) - Live Market Data*"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*💰 Current Price*\n`${quote['current_price']:.2f}` {self._get_price_emoji(quote)}\n{self._format_price_change(quote)}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Open:*\n${quote['open_price']:.2f}"},
                        {"type": "mrkdwn", "text": f"*High:*\n${quote['high_price']:.2f}"},
                        {"type": "mrkdwn", "text": f"*Low:*\n${quote['low_price']:.2f}"},
                        {"type": "mrkdwn", "text": f"*Prev Close:*\n${quote['previous_close']:.2f}"}
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Volume:*\n{quote['volume']:,}"},
                        {"type": "mrkdwn", "text": f"*Market Cap:*\n{self._format_market_cap(quote['market_cap'])}"},
                        {"type": "mrkdwn", "text": f"*P/E Ratio:*\n{quote['pe_ratio']:.1f}"}
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"🟢 Market: *Open* | ⚡ Data: *Real-time* • ⚡ {quote['api_latency_ms']:.0f}ms"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*📊 Price Movement*\n`{self._create_price_chart(quote)}`"
                    }
                },
                {"type": "divider"},
                {
                    "type": "actions",
                    "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "🔴 Auto-Refresh: ON"}, "style": "primary"},
                        {"type": "static_select", "placeholder": {"type": "plain_text", "text": "Overview"}, "options": [
                            {"text": {"type": "plain_text", "text": "Overview"}, "value": "overview"},
                            {"text": {"type": "plain_text", "text": "Detailed"}, "value": "detailed"},
                            {"text": {"type": "plain_text", "text": "Technical"}, "value": "technical"}
                        ]},
                        {"type": "button", "text": {"type": "plain_text", "text": "⭐ Add to Watchlist"}}
                    ]
                }
            ],
            "submit": {"type": "plain_text", "text": "Trade"},
            "close": {"type": "plain_text", "text": "Close"}
        }
        
        return modal
    
    def _get_price_emoji(self, quote: Dict[str, Any]) -> str:
        """Get price change emoji."""
        if quote["price_change"] > 0:
            return "📈"
        elif quote["price_change"] < 0:
            return "📉"
        else:
            return "➡️"
    
    def _format_price_change(self, quote: Dict[str, Any]) -> str:
        """Format price change display."""
        change = quote["price_change"]
        change_pct = quote["price_change_percent"]
        sign = "+" if change > 0 else ""
        return f"{sign}${change:.2f} ({sign}{change_pct:.2f}%)"
    
    def _format_market_cap(self, market_cap: int) -> str:
        """Format market cap."""
        if market_cap >= 1_000_000_000_000:
            return f"${market_cap / 1_000_000_000_000:.2f}T"
        elif market_cap >= 1_000_000_000:
            return f"${market_cap / 1_000_000_000:.2f}B"
        else:
            return f"${market_cap / 1_000_000:.2f}M"
    
    def _create_price_chart(self, quote: Dict[str, Any]) -> str:
        """Create simple price movement chart."""
        change_pct = quote["price_change_percent"]
        bar_length = min(abs(change_pct) * 3, 20)
        bar_char = "█"
        
        if change_pct > 0:
            return f"🟢 {bar_char * int(bar_length)} +{change_pct:.2f}%"
        elif change_pct < 0:
            return f"🔴 {bar_char * int(bar_length)} {change_pct:.2f}%"
        else:
            return "⚪ No change"
    
    def print_modal_preview(self, symbol: str) -> None:
        """Print a text representation of the modal."""
        modal = self.generate_modal_preview(symbol)
        
        if "error" in modal:
            print(f"❌ {modal['error']}")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 ENHANCED /TRADE COMMAND MODAL PREVIEW - {symbol}")
        print(f"{'='*60}")
        
        # Extract and display key information
        quote = self.sample_quotes[symbol]
        
        print(f"\n🔴 LIVE MARKET DATA • Updated {datetime.now().strftime('%H:%M:%S')}")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        print(f"\n📈 {quote['symbol']} ({quote['exchange']}) - Live Market Data")
        print(f"💰 Current Price: ${quote['current_price']:.2f} {self._get_price_emoji(quote)}")
        print(f"   {self._format_price_change(quote)}")
        
        print(f"\n📊 Price Details:")
        print(f"   Open: ${quote['open_price']:.2f}     High: ${quote['high_price']:.2f}")
        print(f"   Low:  ${quote['low_price']:.2f}     Prev: ${quote['previous_close']:.2f}")
        
        print(f"\n📈 Market Information:")
        print(f"   Volume:     {quote['volume']:,}")
        print(f"   Market Cap: {self._format_market_cap(quote['market_cap'])}")
        print(f"   P/E Ratio:  {quote['pe_ratio']:.1f}")
        
        print(f"\n🟢 Market: Open | ⚡ Data: Real-time • {quote['api_latency_ms']:.0f}ms")
        
        print(f"\n📊 Price Movement:")
        print(f"   {self._create_price_chart(quote)}")
        
        print(f"\n🎛️  Controls:")
        print(f"   [AAPL] [TSLA] [MSFT] [GOOGL] [🔄 Refresh]")
        print(f"   🔴 Auto-Refresh: ON | View: Overview | ⭐ Add to Watchlist")
        
        print(f"\n{'='*60}")


def main():
    """Run the enhanced trade command demo."""
    print("🚀 Enhanced /trade Command - Live Market Data Demo")
    print("This demo shows the enhanced market data display capabilities")
    
    demo = MockEnhancedTradeDemo()
    
    # Demo different symbols
    symbols = ["AAPL", "TSLA", "MSFT"]
    
    for symbol in symbols:
        demo.print_modal_preview(symbol)
        print("\n" + "─" * 60)
    
    print("\n✨ Enhanced Features Demonstrated:")
    print("   • Real-time price display with visual indicators")
    print("   • Interactive quick symbol selection buttons")
    print("   • Comprehensive market data (OHLC, Volume, Market Cap)")
    print("   • Price movement visualization")
    print("   • Market status and data quality indicators")
    print("   • Auto-refresh controls")
    print("   • Watchlist functionality")
    print("   • API latency monitoring")
    
    print("\n🎯 Key Improvements over Standard /trade:")
    print("   • Live market data updates (30-second intervals)")
    print("   • Enhanced visual presentation with emojis and formatting")
    print("   • Interactive controls for better user experience")
    print("   • Real-time price change indicators")
    print("   • Quick access to popular stocks")
    print("   • Advanced market data visualization")
    
    print("\n💡 Usage:")
    print("   /trade AAPL    - Open modal with AAPL data")
    print("   /trade         - Open modal for symbol input")
    print("   Click buttons  - Quick symbol selection")
    print("   Toggle refresh - Enable/disable auto-updates")
    
    print("\n🔧 Technical Features:")
    print("   • Finnhub API integration for real-time data")
    print("   • Redis caching for performance")
    print("   • Graceful error handling and fallbacks")
    print("   • Session-based real-time updates")
    print("   • Configurable refresh intervals")
    
    print("\n✅ Ready to integrate with your Slack bot!")
    print("   Import: from enhanced_trade_integration import integrate_enhanced_trade_command")
    print("   Usage:  integrate_enhanced_trade_command(app)")


if __name__ == "__main__":
    main()