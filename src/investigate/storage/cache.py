import os
from investigate.models.holdings import PortfolioSnapshot

def save_snapshot(snapshot: PortfolioSnapshot, filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(snapshot.model_dump_json())

def load_snapshot(filepath: str) -> PortfolioSnapshot | None:
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        content = f.read()
    return PortfolioSnapshot.model_validate_json(content)
