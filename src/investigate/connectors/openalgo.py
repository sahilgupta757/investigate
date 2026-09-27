from datetime import datetime, timezone

import httpx

from investigate.models.holdings import Holding, PortfolioSnapshot


def fetch_holdings(base_url: str) -> PortfolioSnapshot:
    response = httpx.get(f"{base_url}/api/v1/holdings")
    response.raise_for_status()

    data = response.json()
    holdings = []

    for item in data.get("holdings", []):
        holdings.append(
            Holding(
                ticker=item.get("tradingsymbol"),
                isin=item.get("isin"),
                quantity=item.get("quantity"),
                avg_price=item.get("average_price"),
                asset_type="equity",
            )
        )

    return PortfolioSnapshot(
        as_of=datetime.now(timezone.utc), source="openalgo", holdings=holdings
    )
