import httpx
import pytest
from pydantic import ValidationError

from investigate.connectors.openalgo import fetch_holdings


def test_fetch_holdings_success(respx_mock):
    mock_data = {
        "holdings": [
            {
                "tradingsymbol": "TCS",
                "isin": "INE467B01029",
                "quantity": 50,
                "average_price": 3500.0,
                "instrument_token": 123,
            }
        ]
    }
    respx_mock.get("http://openalgo:5000/api/v1/holdings").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    snapshot = fetch_holdings("http://openalgo:5000")
    assert len(snapshot.holdings) == 1
    assert snapshot.holdings[0].ticker == "TCS"
    assert snapshot.source == "openalgo"


def test_fetch_holdings_failure(respx_mock):
    respx_mock.get("http://openalgo:5000/api/v1/holdings").mock(
        return_value=httpx.Response(401)
    )
    with pytest.raises(httpx.HTTPStatusError):
        fetch_holdings("http://openalgo:5000")


def test_fetch_holdings_validation_error(respx_mock):
    # Missing 'average_price'
    mock_data = {
        "holdings": [{"tradingsymbol": "TCS", "isin": "INE467B01029", "quantity": 50}]
    }
    respx_mock.get("http://openalgo:5000/api/v1/holdings").mock(
        return_value=httpx.Response(200, json=mock_data)
    )
    with pytest.raises(ValidationError):
        fetch_holdings("http://openalgo:5000")
