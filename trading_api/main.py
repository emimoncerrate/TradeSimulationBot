from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from decimal import Decimal

# Load environment variables for the API
load_dotenv()

# Import existing services
from services.trading_api import TradingAPIService, get_trading_api_service
from services.market_data import get_market_data_service, MarketQuote

app = FastAPI()


class TradeRequest(BaseModel):
    user_id: str
    ticker: str
    quantity: int
    side: str


@app.post("/simulate_trade")
async def simulate_trade_endpoint(trade_request: TradeRequest):
    trading_service = await get_trading_api_service()

    try:
        market_data_service = await get_market_data_service()
        try:
            market_quote = await market_data_service.get_quote(trade_request.ticker.upper())
        except Exception:
            # Fallback to a mock quote in development when external API is unavailable
            market_quote = MarketQuote(
                symbol=trade_request.ticker.upper(),
                current_price=Decimal("150.00")
            )

        fills, execution_metrics = trading_service.market_simulator.simulate_execution(
            symbol=trade_request.ticker.upper(),
            trade_type=trade_request.side.lower(),
            quantity=abs(trade_request.quantity),
            market_quote=market_quote,
        )

        return {
            "symbol": trade_request.ticker.upper(),
            "side": trade_request.side.lower(),
            "requested_quantity": abs(trade_request.quantity),
            "fills": [f.to_dict() for f in fills],
            "metrics": {
                **execution_metrics,
                "venues_used": [v.value if hasattr(v, "value") else str(v) for v in execution_metrics.get("venues_used", [])],
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"message": "Jain Global Trading API is running"}
