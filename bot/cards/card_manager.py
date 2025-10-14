import json
from pathlib import Path
from botbuilder.core import CardFactory
from botbuilder.schema import Attachment

class CardManager:
    """Manages adaptive cards for the trading bot."""
    
    def __init__(self):
        self.cards_path = Path(__file__).parent
        
    def _load_card_json(self, card_name: str) -> dict:
        """Load a card template from JSON file."""
        card_path = self.cards_path / card_name
        with open(card_path, 'r') as card_file:
            return json.load(card_file)
            
    def create_trade_card(self) -> Attachment:
        """Create a trade order card."""
        card_data = self._load_card_json('trade_card.json')
        return CardFactory.adaptive_card(card_data)
        
    def create_portfolio_card(self, portfolio_data: dict) -> Attachment:
        """Create a portfolio summary card."""
        card_data = {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Portfolio Summary",
                    "size": "Large",
                    "weight": "Bolder"
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {
                            "title": "Total Value:",
                            "value": f"${portfolio_data['total_value']:,.2f}"
                        },
                        {
                            "title": "Daily P/L:",
                            "value": f"${portfolio_data['daily_pnl']:,.2f}"
                        },
                        {
                            "title": "Total P/L:",
                            "value": f"${portfolio_data['total_pnl']:,.2f}"
                        }
                    ]
                }
            ]
        }
        return CardFactory.adaptive_card(card_data)
        
    def create_risk_alert_card(self, risk_data: dict) -> Attachment:
        """Create a risk alert card."""
        card_data = {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Risk Alert",
                    "size": "Large",
                    "weight": "Bolder",
                    "color": "Attention"
                },
                {
                    "type": "TextBlock",
                    "text": risk_data['alert_message'],
                    "wrap": True
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {
                            "title": "Risk Level:",
                            "value": risk_data['risk_level']
                        },
                        {
                            "title": "Impact:",
                            "value": f"${risk_data['potential_impact']:,.2f}"
                        }
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "Acknowledge",
                    "data": {
                        "action": "acknowledge_risk"
                    }
                }
            ]
        }
        return CardFactory.adaptive_card(card_data)
