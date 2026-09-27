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
