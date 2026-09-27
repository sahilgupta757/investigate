# InvestiGate Phase 0 — Holdings Dashboard Design Spec

**Status:** Draft for review
**Date:** 2026-09-27

---

## 1. Goal

Implement Phase 0 of InvestiGate: Fetch current holdings from a local OpenAlgo instance, normalize them into a canonical schema, cache the data to a resilient JSON file, and render a basic dashboard. This phase introduces no AI and no database, focusing purely on connector design, containerization, and handling broker session expiries gracefully.

## 2. Architecture & Containerization

The system will use Docker Compose to orchestrate two isolated services:

- **OpenAlgo Container (`openalgo`):** Uses the official pre-built `marketcalls/openalgo` image. It handles the broker integration. It requires a mounted `.env` for API keys and exposes port 5000 so the user can log in via the browser and establish the daily broker session.
- **InvestiGate Container (`investigate`):** A custom FastAPI application that communicates with the `openalgo` container via the internal Docker network at `http://openalgo:5000`.

## 3. Data Flow & Caching

Because Indian broker sessions expire nightly, fetching fresh holdings on every page load guarantees a broken experience on most days. 

1. The FastApi application attempts to fetch from OpenAlgo.
2. If successful, the application validates the data using Pydantic v2 and immediately writes it to a persistent JSON cache.
3. If the fetch fails (due to session expiry or OpenAlgo being offline), the application reads the last known snapshot from the JSON cache and renders it, displaying a clear "staleness" banner (`as of <timestamp> — broker session expired, reconnect to refresh`).

**Cache Persistence:** 
The InvestiGate container will mount a local `./data` directory from the host to `/app/data` inside the container. The cache file will live at `/app/data/cache.json`, ensuring the snapshot survives container restarts.

## 4. Component Interfaces

### 4.1 Schema (Pydantic v2)
```python
class Holding(BaseModel):
    ticker: str
    isin: str
    quantity: float
    avg_price: float
    asset_type: str = "equity"

class PortfolioSnapshot(BaseModel):
    as_of: datetime
    source: str
    holdings: list[Holding]
```

### 4.2 Connector
```python
def fetch_holdings(base_url: str) -> PortfolioSnapshot:
    # Uses httpx to GET base_url + /api/v1/holdings
```

### 4.3 Cache Storage
```python
def save_snapshot(snapshot: PortfolioSnapshot, filepath: str) -> None:
    # Writes snapshot.model_dump_json() to filepath
    
def load_snapshot(filepath: str) -> PortfolioSnapshot | None:
    # Reads JSON, uses PortfolioSnapshot.model_validate_json()
```

### 4.4 Engine Wrapper
```python
def get_current_portfolio(openalgo_url: str, cache_path: str) -> tuple[PortfolioSnapshot | None, bool]:
    # Orchestrates fetch, save, and fallback-to-load logic.
    # Returns the snapshot and a boolean indicating if it was loaded from a stale cache.
```

## 5. Web Dashboard

- Framework: FastAPI
- Templating: Jinja2 (`/templates/dashboard.html`)
- UI: A simple server-rendered HTML table of holdings, showing total portfolio value, and a Chart.js donut chart for allocation (loaded via CDN). No SPA.
- Resilience: Renders successfully even if the cache file is missing and OpenAlgo is down, showing an empty state with instructions to connect the broker.

## 6. Constraints

- Python 3.12+
- Pydantic v2
- No web dependency in the core parsing/logic (keep FastAPI as a thin wrapper).
- Use `ruff` for formatting and linting.
- Full `pytest` coverage for the connector and cache fallback behavior.
