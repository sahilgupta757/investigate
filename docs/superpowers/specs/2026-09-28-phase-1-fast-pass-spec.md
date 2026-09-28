# Phase 1: Fast Pass & Grounding Validator

**Status:** Approved
**Date:** 2026-09-28

## 1. Purpose
Implement Phase 1 of InvestiGate: a fast, structured portfolio health check that enriches the portfolio with fundamental data and uses an LLM to evaluate it. The core feature is the **Grounding Validator**, a hard gate that prevents the LLM from hallucinating numbers or doing unauthorized arithmetic.

## 2. Architecture & Components
Three new core modules in `src/investigate/engine/`:

### 2.1 `enrichment.py` (Facts Payload Builder)
- Takes a `PortfolioSnapshot`.
- Uses `yfinance` to fetch current price, sector, trailing P/E, market cap, and 52-week high/low for each ticker.
- Tries `.NS` first for Indian tickers, falls back to `.BO`.
- Calculates portfolio allocations (percentages) deterministically.
- Bundles everything into a flat, structured dictionary/Pydantic model called `FactsPayload`.

### 2.2 `prompts.py` (LLM Integration)
- Connects to the LLM via OpenRouter using the `openai` Python SDK.
- Targets `google/gemini-2.5-flash` or similar free tier models.
- Defines a strict `PortfolioReview` Pydantic schema for structured output (e.g., summary, strengths, concentration_risks, valuation_anomalies).
- Instructs the LLM to handle `null` fields gracefully and to avoid using formatting suffixes for numbers (like 'M' or 'B') so the validator can parse them.
- Feeds the `FactsPayload` as JSON to the LLM and prompts it for the review.

### 2.3 `validator.py` (Grounding Validator)
- Intercepts the LLM's raw text/JSON response.
- Extracts all numeric tokens using regex (e.g., `[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?`).
- Asserts each extracted number exists in the `FactsPayload` values by recursively scanning the payload dict.
- Uses `math.isclose` to allow for reasonable decimal rounding (e.g., matching `17.3` to `17.34`).
- **Hard Gate:** If any number is unmatched, it raises a `HallucinationError`. The system will fail loudly rather than showing ungrounded numbers to the user.

## 3. Data Flow
1. User requests a portfolio review via the FastAPI backend.
2. Backend pulls the cached OpenAlgo snapshot.
3. `enrichment.py` builds the `FactsPayload`.
4. The LLM generates a structured review based on the payload.
5. `validator.py` checks every number in the review against the payload.
6. If valid, the review is passed to the frontend and rendered in the dashboard.

## 4. Error Handling
- **Missing yfinance Data:** Missing fields are populated as `null`. The LLM prompt explicitly instructs it to handle `null` gracefully.
- **Hallucinations:** If `HallucinationError` is raised, the API returns a 500-level error with a clear message: "Analysis Blocked: The AI hallucinated a numeric value not found in the source data." The UI displays this as a red error banner.

## 5. Testing
- **Validator Unit Tests:** Strict tests passing fake LLM strings with invented numbers and derived math to prove the validator catches them.
- **Mocked Enrichment:** `yfinance` network calls are mocked in the test suite to ensure tests remain fast, offline, and deterministic.
