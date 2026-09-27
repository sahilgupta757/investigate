# Phase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch current holdings from OpenAlgo via a Docker service, normalize them using Pydantic v2, cache to a JSON file mounted via volume, and render a basic dashboard.

**Architecture:** A `docker-compose.yml` defining an `openalgo` service (using `marketcalls/openalgo`) and an `investigate` FastAPI service. The FastAPI app calls `http://openalgo:5000/api/v1/holdings`, validates data with Pydantic v2, and saves it to a mounted `/app/data/cache.json`.

**Tech Stack:** Docker Compose, Python 3.12+, FastAPI, Pydantic v2, httpx, Jinja2.

**Spec:** `docs/superpowers/specs/2026-09-27-phase-0-holdings-spec.md`

## Global Constraints

- Python 3.12+, type hints everywhere
- Use Pydantic v2
- Use `ruff` for linting and formatting
- Tests with `pytest`
- No web dependency in the core parsing/logic (keep FastAPI as a thin wrapper).

## Review Focus

- OpenAlgo returns a non-200 response or network error: Expected behavior is to fallback to the cached JSON and display a staleness banner.
- Cache file does not exist on first run and OpenAlgo fails: Expected behavior is an empty state with instructions to connect the broker.
- Invalid Pydantic v2 validation (missing fields): Expected behavior is fallback to cache.

---

### Task 1: Docker and Project Initialization

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `requirements.txt`

**Interfaces:**
- Produces: Docker infrastructure.

- [ ] **Step 1: Write `requirements.txt`**
Content:
```
fastapi
uvicorn
pydantic>=2.0.0
httpx
jinja2
pytest
pytest-mock
respx
```

- [ ] **Step 2: Write `Dockerfile`**
Content:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app/src
CMD ["uvicorn", "investigate.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Write `docker-compose.yml`**
Content:
```yaml
services:
  openalgo:
    image: marketcalls/openalgo:latest
    ports:
      - "5000:5000"
    volumes:
      - ./openalgo-data:/app/data
      - ./.env:/app/.env

  investigate:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src
      - ./data:/app/data
    depends_on:
      - openalgo
```

- [ ] **Step 4: Commit**
```bash
git add Dockerfile docker-compose.yml requirements.txt
git commit -m "chore: add docker compose and requirements"
```

### Task 2: Core Domain Models

**Files:**
- Create: `src/investigate/models/holdings.py`
- Test: `tests/models/test_holdings.py`

**Interfaces:**
- Produces: `Holding` model, `PortfolioSnapshot` model

- [ ] **Step 1: Write the failing test**

```python
from datetime import datetime, timezone
from investigate.models.holdings import Holding, PortfolioSnapshot
from pydantic import ValidationError
import pytest

def test_portfolio_snapshot_creation():
    holding = Holding(ticker="RELIANCE", isin="INE002A01018", quantity=10, avg_price=2500.50, asset_type="equity")
    snapshot = PortfolioSnapshot(
        as_of=datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
        source="openalgo",
        holdings=[holding]
    )
    assert snapshot.holdings[0].ticker == "RELIANCE"
    assert snapshot.source == "openalgo"

def test_holding_validation_missing_fields():
    with pytest.raises(ValidationError):
        Holding(ticker="RELIANCE", quantity=10) # missing isin, avg_price
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/models/test_holdings.py -v`
Expected: FAIL

- [ ] **Step 3: Implement domain models in `src/investigate/models/holdings.py`**
Use Pydantic v2 `BaseModel`. Define `Holding` and `PortfolioSnapshot` as per spec.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/models/test_holdings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/investigate/models/holdings.py tests/models/test_holdings.py
git commit -m "feat: core holdings pydantic v2 models"
```

### Task 3: Connector and Cache Layer

**Files:**
- Create: `src/investigate/connectors/openalgo.py`
- Create: `src/investigate/storage/cache.py`
- Test: `tests/connectors/test_openalgo.py`
- Test: `tests/storage/test_cache.py`

**Interfaces:**
- Consumes: `Holding`, `PortfolioSnapshot`
- Produces: `fetch_holdings(base_url: str) -> PortfolioSnapshot`, `save_snapshot(snapshot: PortfolioSnapshot, filepath: str) -> None`, `load_snapshot(filepath: str) -> PortfolioSnapshot | None`

- [ ] **Step 1: Write tests for OpenAlgo connector**
Use `respx_mock` to mock `http://openalgo:5000/api/v1/holdings`. Test success and failure (e.g. 401). Test missing fields resulting in ValidationError bubble up.

- [ ] **Step 2: Write tests for Cache layer**
Test `save_snapshot` using `snapshot.model_dump_json()`. Test `load_snapshot` using `PortfolioSnapshot.model_validate_json()`. Test `load_snapshot` on missing file returns `None`.

- [ ] **Step 3: Run tests to verify they fail**
Run: `pytest tests/connectors/test_openalgo.py tests/storage/test_cache.py -v`
Expected: FAIL

- [ ] **Step 4: Implement OpenAlgo connector and Cache layer**
Implement the methods mapping JSON from OpenAlgo to the `Holding` objects. Implement cache reading/writing to standard Python file IO using Pydantic v2 methods.

- [ ] **Step 5: Run tests to verify they pass**
Run: `pytest tests/connectors/test_openalgo.py tests/storage/test_cache.py -v`
Expected: PASS

- [ ] **Step 6: Commit**
```bash
git add src/investigate/connectors/openalgo.py src/investigate/storage/cache.py tests/connectors/test_openalgo.py tests/storage/test_cache.py
git commit -m "feat: openalgo connector and file cache persistence"
```

### Task 4: Portfolio Manager (The Engine Wrapper)

**Files:**
- Create: `src/investigate/engine/portfolio.py`
- Test: `tests/engine/test_portfolio.py`

**Interfaces:**
- Consumes: `fetch_holdings`, `save_snapshot`, `load_snapshot`
- Produces: `get_current_portfolio(openalgo_url: str, cache_path: str) -> tuple[PortfolioSnapshot | None, bool]`

- [ ] **Step 1: Write the failing tests**
Test `get_current_portfolio` fresh fetch (mock `fetch_holdings`). Test `get_current_portfolio` stale fallback (mock `fetch_holdings` to throw error, mock `load_snapshot` returning cache).

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/engine/test_portfolio.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `get_current_portfolio`**
Implement the orchestration logic: fetch, if success save & return (snapshot, False). If error, load & return (snapshot, True).

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/engine/test_portfolio.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/investigate/engine/portfolio.py tests/engine/test_portfolio.py
git commit -m "feat: portfolio manager orchestration"
```

### Task 5: FastAPI Application & Dashboard

**Files:**
- Create: `src/investigate/web/app.py`
- Create: `src/investigate/web/templates/dashboard.html`
- Test: `tests/web/test_app.py`

**Interfaces:**
- Consumes: `get_current_portfolio`
- Produces: FastAPI app

- [ ] **Step 1: Write the failing test**
Use `TestClient` from FastAPI. Mock `get_current_portfolio`. Test `GET /` returns 200 and renders HTML.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/web/test_app.py -v`
Expected: FAIL

- [ ] **Step 3: Implement FastAPI app and template**
In `app.py`, define FastAPI app and Jinja2 templates. Pass computed totals and `is_stale` boolean to template. In `dashboard.html`, display the tables and banner.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest tests/web/test_app.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add src/investigate/web/app.py src/investigate/web/templates/dashboard.html tests/web/test_app.py
git commit -m "feat: fastApi dashboard"
```
