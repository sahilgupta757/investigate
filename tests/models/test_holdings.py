from datetime import datetime, timezone
from investigate.models.holdings import Holding, PortfolioSnapshot
from pydantic import ValidationError
import pytest

def test_portfolio_snapshot_creation():
    holding = Holding(ticker="RELIANCE", isin="INE002A01018", quantity=10, avg_price=2500.50, asset_type="equity")
    snapshot = PortfolioSnapshot(
        as_of=datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
        source="openalgo",
        holdings=[holding]
    )
    assert snapshot.holdings[0].ticker == "RELIANCE"
    assert snapshot.source == "openalgo"

def test_holding_validation_missing_fields():
    with pytest.raises(ValidationError):
        Holding(ticker="RELIANCE", quantity=10) # missing isin, avg_price
