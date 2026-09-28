import pytest
from investigate.engine.enrichment import build_facts_payload, FactsPayload
from investigate.models.holdings import PortfolioSnapshot, Holding
from datetime import datetime

def test_build_facts_payload_success(mocker):
    snapshot = PortfolioSnapshot(
        as_of=datetime.now(),
        source="test",
        holdings=[Holding(ticker="RELIANCE", isin="123", quantity=10.0, avg_price=2500.0, asset_type="EQUITY")]
    )
    
    mock_ticker = mocker.patch("yfinance.Ticker")
    mock_ticker.return_value.info = {"sector": "Energy", "trailingPE": 20.5, "marketCap": 1000000, "currentPrice": 2600.0, "fiftyTwoWeekHigh": 3000.0, "fiftyTwoWeekLow": 2000.0}
    
    payload = build_facts_payload(snapshot)
    assert payload.total_value == 26000.0 # using current_price for total value, since 10 * 2600 = 26000
    assert payload.holdings_data["RELIANCE"].sector == "Energy"
    assert payload.holdings_data["RELIANCE"].current_price == 2600.0

def test_build_facts_payload_yfinance_failure(mocker):
    snapshot = PortfolioSnapshot(
        as_of=datetime.now(),
        source="test",
        holdings=[Holding(ticker="UNKNOWN", isin="123", quantity=10.0, avg_price=100.0, asset_type="EQUITY")]
    )
    
    # Mock yfinance to raise an exception
    mock_ticker = mocker.patch("yfinance.Ticker")
    mock_ticker.side_effect = Exception("Network timeout")
    
    payload = build_facts_payload(snapshot)
    
    assert payload.total_value == 1000.0 # Falls back to avg_price
    assert payload.holdings_data["UNKNOWN"].sector is None
    assert payload.holdings_data["UNKNOWN"].current_price is None
