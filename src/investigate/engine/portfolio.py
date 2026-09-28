import httpx
from pydantic import ValidationError

from investigate.connectors.openalgo import fetch_holdings
from investigate.models.holdings import PortfolioSnapshot
from investigate.storage.cache import load_snapshot, save_snapshot


def get_current_portfolio(
    openalgo_url: str, api_key: str, cache_path: str
) -> tuple[PortfolioSnapshot | None, bool]:
    try:
        snapshot = fetch_holdings(openalgo_url, api_key)
        save_snapshot(snapshot, cache_path)
        return snapshot, False
    except (httpx.RequestError, httpx.HTTPStatusError, ValidationError, Exception):
        try:
            snapshot = load_snapshot(cache_path)
            return snapshot, snapshot is not None
        except Exception:
            return None, False
