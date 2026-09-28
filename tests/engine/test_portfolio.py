from datetime import datetime, timezone
from unittest.mock import patch

import httpx
from pydantic import ValidationError

from investigate.engine.portfolio import get_current_portfolio
from investigate.models.holdings import PortfolioSnapshot


def test_get_portfolio_fresh():
    dummy = PortfolioSnapshot(
        as_of=datetime.now(timezone.utc), source="openalgo", holdings=[]
    )
    with (
        patch(
            "investigate.engine.portfolio.fetch_holdings", return_value=dummy
        ) as mock_fetch,
        patch("investigate.engine.portfolio.save_snapshot") as mock_save,
    ):
        snapshot, is_stale = get_current_portfolio("http://url", "dummy_key", "cache.json")
        assert not is_stale
        assert snapshot is dummy
        mock_save.assert_called_once_with(dummy, "cache.json")


def test_get_portfolio_stale_fallback():
    dummy_cache = PortfolioSnapshot(
        as_of=datetime.now(timezone.utc), source="openalgo", holdings=[]
    )
    with (
        patch(
            "investigate.engine.portfolio.fetch_holdings",
            side_effect=httpx.RequestError("error"),
        ),
        patch(
            "investigate.engine.portfolio.load_snapshot", return_value=dummy_cache
        ) as mock_load,
    ):
        snapshot, is_stale = get_current_portfolio("http://url", "dummy_key", "cache.json")
        assert is_stale
        assert snapshot is dummy_cache
        mock_load.assert_called_once_with("cache.json")


def test_get_portfolio_validation_fallback():
    dummy_cache = PortfolioSnapshot(
        as_of=datetime.now(timezone.utc), source="openalgo", holdings=[]
    )
    with (
        patch(
            "investigate.engine.portfolio.fetch_holdings",
            side_effect=ValidationError.from_exception_data("error", []),
        ),
        patch(
            "investigate.engine.portfolio.load_snapshot", return_value=dummy_cache
        ) as mock_load,
    ):
        snapshot, is_stale = get_current_portfolio("http://url", "dummy_key", "cache.json")
        assert is_stale
        assert snapshot is dummy_cache
        mock_load.assert_called_once_with("cache.json")


def test_get_portfolio_empty_state():
    with (
        patch(
            "investigate.engine.portfolio.fetch_holdings",
            side_effect=httpx.RequestError("error"),
        ),
        patch("investigate.engine.portfolio.load_snapshot", return_value=None),
    ):
        snapshot, is_stale = get_current_portfolio("http://url", "dummy_key", "cache.json")
        assert not is_stale
        assert snapshot is None
