from datetime import datetime, timezone

from investigate.models.holdings import Holding, PortfolioSnapshot
from investigate.storage.cache import load_snapshot, save_snapshot


def test_save_and_load_snapshot(tmp_path):
    filepath = tmp_path / "cache.json"
    snapshot = PortfolioSnapshot(
        as_of=datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
        source="openalgo",
        holdings=[
            Holding(
                ticker="HDFC",
                isin="123",
                quantity=10,
                avg_price=100.0,
                asset_type="equity",
            )
        ],
    )
    save_snapshot(snapshot, str(filepath))

    loaded = load_snapshot(str(filepath))
    assert loaded is not None
    assert loaded.holdings[0].ticker == "HDFC"
    assert loaded.as_of == snapshot.as_of


def test_load_nonexistent_snapshot(tmp_path):
    filepath = tmp_path / "does_not_exist.json"
    loaded = load_snapshot(str(filepath))
    assert loaded is None
