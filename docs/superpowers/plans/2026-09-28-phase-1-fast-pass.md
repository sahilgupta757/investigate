# Phase 1: Fast Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a fast, structured portfolio health check that uses `yfinance` to enrich the portfolio, an LLM to evaluate it, and a hard-gate validator to prevent numeric hallucinations.

**Architecture:** A three-stage pipeline. The `enrichment` module builds a deterministic Facts Payload. The `prompts` module passes this payload to Gemini (using `google-genai` structured outputs). The `validator` module intercepts the response, extracting all numbers via regex and enforcing exact or rounded matches against the payload.

**Tech Stack:** `yfinance`, `google-genai`, `pydantic`, `re`

**Spec:** `docs/superpowers/specs/2026-09-28-phase-1-fast-pass-spec.md`

## Global Constraints

- Must run completely offline from the broker (using the cached snapshot).
- No arithmetic logic permitted in the LLM.
- Model must use Gemini via the official `google-genai` SDK.
- The grounding validator must raise an exception on failure, not silently redact.

## Review Focus

- **yfinance Network Failure:** A ticker might not exist or the network might time out. The payload should insert `None` and the validator/LLM should survive. Test: Mock `yfinance.Ticker.info` to raise an Exception.
- **Validator Tolerance:** The LLM might output `17.3` for `17.34`. The validator should use a tolerance matching logic (e.g. `math.isclose` or string prefix). Test: Pass `17.34` in payload and `17.3` in prose.
- **Empty Portfolio:** The cache might have zero holdings. The fast pass should return a trivial empty review rather than crashing. Test: Pass an empty snapshot.

---

### Task 1: Enrichment Module

**Files:**
- Create: `src/investigate/engine/enrichment.py`
- Test: `tests/engine/test_enrichment.py`

**Interfaces:**
- Consumes: `PortfolioSnapshot` from `src/investigate/models/holdings.py`
- Produces: `FactsPayload` (Pydantic model) and `build_facts_payload(snapshot: PortfolioSnapshot) -> FactsPayload`

- [ ] **Step 1: Write the failing test**

```python
from investigate.engine.enrichment import build_facts_payload, FactsPayload
from investigate.models.holdings import PortfolioSnapshot, Holding
from datetime import datetime

def test_build_facts_payload_success(mocker):
    snapshot = PortfolioSnapshot(
        as_of=datetime.now(),
        source="test",
        holdings=[Holding(ticker="RELIANCE", isin="123", quantity=10.0, average_price=2500.0, asset_type="EQUITY")]
    )
    
    mock_ticker = mocker.patch("yfinance.Ticker")
    mock_ticker.return_value.info = {"sector": "Energy", "trailingPE": 20.5, "marketCap": 1000000, "currentPrice": 2600.0, "fiftyTwoWeekHigh": 3000.0, "fiftyTwoWeekLow": 2000.0}
    
    payload = build_facts_payload(snapshot)
    assert payload.total_value == 25000.0
    assert payload.holdings_data["RELIANCE"].sector == "Energy"
    assert payload.holdings_data["RELIANCE"].current_price == 2600.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/test_enrichment.py -v`
Expected: FAIL with "ModuleNotFoundError" or similar.

- [ ] **Step 3: Implement `FactsPayload` and `build_facts_payload` in `src/investigate/engine/enrichment.py`**

Define `EnrichedHolding` and `FactsPayload` Pydantic models. Include fields: `sector`, `pe_ratio`, `market_cap`, `current_price`, `fifty_two_week_high`, `fifty_two_week_low`, `allocation_percentage`. Iterate over the snapshot, query `yfinance.Ticker(f"{h.ticker}.NS")`, fallback to `.BO` if `.NS` throws or returns empty. Handle `Exception` by using `None` for fields, calculate `total_value` and individual `allocation_percentage`, and return the `FactsPayload`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/engine/test_enrichment.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/investigate/engine/enrichment.py tests/engine/test_enrichment.py
git commit -m "feat: implement enrichment module with yfinance"
```

---

### Task 2: Grounding Validator

**Files:**
- Create: `src/investigate/engine/validator.py`
- Test: `tests/engine/test_validator.py`

**Interfaces:**
- Consumes: `FactsPayload` (from Task 1) and raw JSON string from LLM.
- Produces: `validate_grounding(review_json: str, facts: FactsPayload) -> None`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from investigate.engine.validator import validate_grounding, HallucinationError
from investigate.engine.enrichment import FactsPayload, EnrichedHolding

def test_validate_grounding_success():
    facts = FactsPayload(total_value=100.5, holdings_data={"A": EnrichedHolding(sector="Tech", market_cap=50.0, pe_ratio=15.2, current_price=10.0, allocation_percentage=100.0, fifty_two_week_high=20.0, fifty_two_week_low=5.0)})
    review = '{"summary": "Total is 100.5 and PE is 15.2"}'
    validate_grounding(review, facts)  # Should not raise

def test_validate_grounding_hallucination():
    facts = FactsPayload(total_value=100.0, holdings_data={})
    review = '{"summary": "Total is 100.0 but I invented 42.5"}'
    with pytest.raises(HallucinationError):
        validate_grounding(review, facts)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engine/test_validator.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `validate_grounding` in `src/investigate/engine/validator.py`**

Define `HallucinationError(Exception)`.
Use `re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', review_json)`.
Write a recursive function to walk `FactsPayload.model_dump()` to gather a set of all valid numbers (floats/ints).
For each extracted string, cast to float. If it doesn't match any valid number (using `math.isclose(extracted, valid, rel_tol=1e-2)` to allow minor rounding), raise `HallucinationError`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/engine/test_validator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/investigate/engine/validator.py tests/engine/test_validator.py
git commit -m "feat: implement grounding validator"
```

---

### Task 3: LLM Integration

**Files:**
- Create: `src/investigate/engine/prompts.py`
- Test: `tests/engine/test_prompts.py`
- Modify: `requirements.txt`

**Interfaces:**
- Consumes: `FactsPayload` and `validate_grounding`.
- Produces: `PortfolioReview` (Pydantic) and `generate_fast_pass(facts: FactsPayload, api_key: str) -> PortfolioReview`

- [ ] **Step 1: Add `google-genai` to dependencies**

Add `google-genai` to `requirements.txt` and install it.

- [ ] **Step 2: Write the failing test**

```python
from investigate.engine.prompts import generate_fast_pass, PortfolioReview
from investigate.engine.enrichment import FactsPayload

def test_generate_fast_pass(mocker):
    facts = FactsPayload(total_value=100.0, holdings_data={})
    
    mock_client = mocker.patch("google.genai.Client")
    mock_response = mocker.MagicMock()
    mock_response.text = '{"summary": "Good", "strengths": [], "concentration_risks": [], "valuation_anomalies": []}'
    mock_client.return_value.models.generate_content.return_value = mock_response
    
    mocker.patch("investigate.engine.prompts.validate_grounding")
    
    review = generate_fast_pass(facts, "dummy_key")
    assert review.summary == "Good"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/engine/test_prompts.py -v`
Expected: FAIL

- [ ] **Step 4: Implement LLM caller in `src/investigate/engine/prompts.py`**

Define `PortfolioReview` Pydantic model with fields: `summary`, `strengths`, `concentration_risks`, `valuation_anomalies`.
Create a system instruction requiring the model to handle `null` gracefully, and crucially, to NOT output numbers with formatting suffixes (like "B" or "M") so the numeric validator can verify raw quantities perfectly.
Initialize `google.genai.Client(api_key=api_key)`.
Call `models.generate_content(model='gemini-2.5-flash', contents=..., config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=PortfolioReview, system_instruction=...))`.
Pass `response.text` to `validate_grounding(response.text, facts)`.
Return `PortfolioReview.model_validate_json(response.text)`.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/engine/test_prompts.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt src/investigate/engine/prompts.py tests/engine/test_prompts.py
git commit -m "feat: implement Gemini LLM integration for fast pass"
```

---

### Task 4: Fast Pass API & UI

**Files:**
- Modify: `src/investigate/web/app.py`
- Modify: `src/investigate/web/templates/dashboard.html`

**Interfaces:**
- Consumes: `generate_fast_pass` and `build_facts_payload`.

- [ ] **Step 1: Add GEMINI_API_KEY to `.env` requirement**

Update `docker-compose.yml` and `app.py` to require `GEMINI_API_KEY`.

- [ ] **Step 2: Add Fast Pass endpoint to `app.py`**

Add `POST /api/fast-pass` that loads the cached snapshot, builds the facts payload, calls `generate_fast_pass`, and returns the `PortfolioReview` JSON. Catch `HallucinationError` and return a 500 JSON response with the error string.

- [ ] **Step 3: Update `dashboard.html`**

Add a "Run AI Health Check" button below the chart. When clicked, fetch `/api/fast-pass`.
On success, render a styled div showing the Strengths, Risks, and Anomalies.
On error, display a red banner with the exception message.

- [ ] **Step 4: Manually test and commit**

```bash
git add src/investigate/web/ docker-compose.yml
git commit -m "feat: integrate Fast Pass into web UI"
```
