from investigate.models.holdings import PortfolioSnapshot
from pydantic import BaseModel
from typing import Optional
import yfinance as yf

class EnrichedHolding(BaseModel):
    sector: Optional[str] = None
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    current_price: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    allocation_percentage: Optional[float] = None

class FactsPayload(BaseModel):
    total_value: float
    holdings_data: dict[str, EnrichedHolding]

def build_facts_payload(snapshot: PortfolioSnapshot) -> FactsPayload:
    holdings_data = {}
    total_value = 0.0

    for h in snapshot.holdings:
        ticker = h.ticker
        info = None
        # Try .NS first for Indian equities
        try:
            yt = yf.Ticker(f"{ticker}.NS")
            info = yt.info
            if not info or "currentPrice" not in info:
                raise Exception("Missing info")
        except Exception:
            # Fallback to .BO
            try:
                yt = yf.Ticker(f"{ticker}.BO")
                info = yt.info
            except Exception:
                info = {}
                
        if info is None:
            info = {}

        current_price = info.get("currentPrice")
        
        # We need a price for allocation. If current_price is missing, fallback to avg_price
        price_for_calc = current_price if current_price is not None else h.avg_price
        total_value += h.quantity * price_for_calc

        holdings_data[ticker] = EnrichedHolding(
            sector=info.get("sector"),
            pe_ratio=info.get("trailingPE"),
            market_cap=info.get("marketCap"),
            current_price=current_price,
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
            allocation_percentage=None  # We'll calculate this after getting total_value
        )
        
    for ticker, h_data in holdings_data.items():
        original_holding = next(h for h in snapshot.holdings if h.ticker == ticker)
        price_for_calc = h_data.current_price if h_data.current_price is not None else original_holding.avg_price
        
        if total_value > 0:
            h_data.allocation_percentage = (original_holding.quantity * price_for_calc / total_value) * 100
        else:
            h_data.allocation_percentage = 0.0

    return FactsPayload(
        total_value=total_value,
        holdings_data=holdings_data
    )
