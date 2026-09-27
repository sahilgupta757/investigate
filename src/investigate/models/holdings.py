from datetime import datetime

from pydantic import BaseModel


class Holding(BaseModel):
    ticker: str
    isin: str
    quantity: float
    avg_price: float
    asset_type: str = "equity"


class PortfolioSnapshot(BaseModel):
    as_of: datetime
    source: str
    holdings: list[Holding]

    @property
    def total_value(self) -> float:
        return sum(h.quantity * h.avg_price for h in self.holdings)

    @property
    def allocations(self) -> list[dict]:
        tot = self.total_value
        if tot <= 0:
            return []
        return [
            {
                "ticker": h.ticker,
                "percentage": (h.quantity * h.avg_price / tot) * 100,
            }
            for h in self.holdings
        ]
