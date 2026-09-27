import httpx
from pydantic import ValidationError
from investigate.models.holdings import PortfolioSnapshot
from investigate.connectors.openalgo import fetch_holdings
from investigate.storage.cache import save_snapshot, load_snapshot

def get_current_portfolio(openalgo_url: str, cache_path: str) -> tuple[PortfolioSnapshot | None, bool]:
    try:
        snapshot = fetch_holdings(openalgo_url)
        save_snapshot(snapshot, cache_path)
        return snapshot, False
    except (httpx.RequestError, httpx.HTTPStatusError, ValidationError, Exception):
        snapshot = load_snapshot(cache_path)
        return snapshot, snapshot is not None
