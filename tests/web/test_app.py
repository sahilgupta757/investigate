import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from investigate.models.holdings import PortfolioSnapshot, Holding

def test_dashboard_renders():
    # we must import app inside or patch before import if app initializes during import.
    # To be safe, patch first.
    with patch("investigate.web.app.get_current_portfolio") as mock_get:
        dummy = PortfolioSnapshot(
            as_of=datetime.now(timezone.utc),
            source="openalgo",
            holdings=[Holding(ticker="RELIANCE", isin="123", quantity=10, avg_price=2500, asset_type="equity")]
        )
        mock_get.return_value = (dummy, False)
        
        from investigate.web.app import app
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "RELIANCE" in response.text
        assert "Chart.js" in response.text or "chart.js" in response.text

def test_dashboard_empty_state():
    with patch("investigate.web.app.get_current_portfolio") as mock_get:
        mock_get.return_value = (None, False)
        from investigate.web.app import app
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "log into OpenAlgo" in response.text or "connect the broker" in response.text
