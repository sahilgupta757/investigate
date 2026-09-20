# Nivesh — Design Spec

**Status:** Draft for review
**Date:** 2026-09-21
**Working title:** Nivesh (निवेश, "investment") — rename freely.

---

## 1. Purpose

Nivesh is an agentic RAG system for Indian equity research. It reads a real
brokerage portfolio, grounds its analysis in primary source documents
(annual reports, filings, earnings-call transcripts), and produces a
portfolio review where every number is traceable to a deterministic source
and every qualitative claim carries a citation.

It serves two goals at once, and the design is explicitly shaped by both:

**Product goal.** Replace a manual, session-by-session research workflow
(currently a Claude Code skill) with a standing tool that reviews the whole
portfolio, not one name at a time.

**Learning goal.** Build end-to-end retrieval and agentic infrastructure from
primitives, with evaluation and observability, as demonstrable evidence of
applied AI engineering depth.

### 1.1 Why RAG is genuine here, not decorative

The existing research workflow has one acknowledged, structural blind spot:
**governance**. Promoter pledging, auditor qualifications and resignations,
related-party transactions, shareholding-pattern drift and contingent
liabilities are not available from any free structured API. They exist only
as prose, inside 100-300 page PDFs.

This is the textbook conditions for retrieval: large unstructured corpora,
semantic rather than keyword questions, and mandatory citation back to a
source page. The system's most valuable feature and its RAG layer are the
same thing.

Two secondary corpora extend this:
- **Earnings-call transcripts across quarters** — detecting drift in
  management guidance over time.
- **The system's own past analysis log** — retrieval over prior theses to
  surface where a view changed, and whether it was wrong.

### 1.2 Where RAG is deliberately NOT used

Numeric fundamentals — P/E, EV/EBITDA, margins, NAVs, rolling CAGRs — are
**never** embedded or retrieved semantically. They are structured data,
fetched deterministically and passed to the model as JSON. Vector search over
numbers degrades retrieval precision and materially increases hallucination
risk.

This boundary is a load-bearing design decision, not an optimization.

---

## 2. Non-goals

- **No order placement.** Read-only. The system never trades.
- **No mutual funds in v1.** Broker APIs surface equity/derivative holdings;
  MF folio data is not reliably available through the same path. Deferred to
  a later phase with a separate data source.
- **No intraday, F&O, options or swing-trading signals.** Horizons are
  1-3 years (short) and 3-7 years (long).
- **No multi-user SaaS.** Single-user, self-hosted, localhost. No auth layer,
  no tenancy, no hosted deployment.
- **No historical portfolio time-series in v1.** One cached snapshot only
  (see 5.1); full history is a later phase.
- **No RAG framework.** LlamaIndex/LangChain are deliberately excluded from
  the core retrieval path (see 9.1).

---

## 3. Success criteria

### Product
- Opens to a dashboard showing current holdings with allocation and
  concentration, working even when the broker session has expired.
- A fast pass over the whole portfolio in under ~30 seconds, with zero
  ungrounded numbers.
- A deep dive on any single holding that cites specific pages of specific
  filings, and that surfaces at least one governance signal not available
  from structured APIs.

### Learning (the acceptance bar that matters for the career goal)
- Retrieval quality is **measured, not asserted**: a golden evaluation set
  exists, and recall@k / MRR / nDCG are reported before and after reranking.
- A grounding validator provably rejects fabricated numbers and citations,
  with tests demonstrating it catching both.
- Every LLM call is traced with token count, cost and latency.
- The eval suite runs in CI and fails the build on regression.
- The architecture is written up publicly, including what was measured and
  what did not work.

---

## 4. Architecture

```
                    ┌──────────────────────────────┐
   OpenAlgo  ──────▶│  Connector layer             │
   (self-hosted,    │  → canonical Holding schema  │
    broker auth)    │  → snapshot cache (JSON)     │
                    └──────────────┬───────────────┘
                                   │
   yfinance / APIs ───────────────▶│  Structured facts store (Postgres)
                                   │  numbers ONLY, never embedded
                                   │
   Filings, annual   ┌─────────────▼───────────────┐
   reports, calls ──▶│  Ingestion (Temporal)       │
                     │  parse → chunk → embed      │
                     └─────────────┬───────────────┘
                                   │
                     ┌─────────────▼───────────────┐
                     │  Hybrid index               │
                     │  pgvector (dense)           │
                     │  Elasticsearch (BM25)       │
                     │  → RRF → cross-encoder      │
                     └─────────────┬───────────────┘
                                   │
                     ┌─────────────▼───────────────┐
                     │  Agent layer                │
                     │  analyst → red-team critic  │
                     └─────────────┬───────────────┘
                                   │
                     ┌─────────────▼───────────────┐
                     │  Grounding validator        │
                     │  (hard gate — fails loudly) │
                     └─────────────┬───────────────┘
                                   │
                     ┌─────────────▼───────────────┐
                     │  FastAPI + server-rendered  │
                     │  dashboard (thin)           │
                     └─────────────────────────────┘
```

The core principle: **the analysis engine is a plain Python package with no
web dependency.** FastAPI is a thin wrapper over it. This keeps the engine
independently testable and makes a CLI entry point or a scheduled report mode
nearly free later.

---

## 5. Component specifications

### 5.1 Connector layer

**Does:** pulls current holdings and normalizes them.

**Interface:** `fetch_holdings() -> PortfolioSnapshot`

```python
Holding        { ticker, isin, quantity, avg_price, asset_type }
PortfolioSnapshot { as_of: datetime, source: str, holdings: list[Holding] }
```

**Depends on:** a self-hosted OpenAlgo instance, authenticated to the user's
broker. Nivesh never handles broker credentials directly — it only calls
OpenAlgo's local REST API.

**Critical constraint.** Indian broker tokens expire nightly by regulation,
and OpenAlgo's holdings endpoint requires a live broker session. Any design
that fetches fresh data on every page load is broken on most days.

**Therefore:** every successful pull is written to a single JSON cache file.
On failure the dashboard renders the cached snapshot with a visible banner:
`as of <timestamp> — broker session expired, reconnect to refresh`. This is
one file and one timestamp, not a history feature.

### 5.2 Structured facts store

**Does:** holds all numeric data — prices, ratios, growth rates, margins,
analyst spreads.

**Why Postgres and not the vector store:** these values are queried exactly,
not semantically, and they are the inputs the grounding validator checks the
model's output against. They must be addressable as data, not as text.

### 5.3 Ingestion pipeline

**Does:** turns source documents into retrievable, cited chunks.

**Stages:** fetch → parse → chunk → embed → index.

- **Fetch.** Annual reports and filings for held tickers.
- **Parse.** PyMuPDF. Tables in Indian annual reports are genuinely hard —
  multi-column layouts, scanned pages, footnote-heavy financial statements.
  Expect this to be the most underestimated work in the project.
- **Chunk.** Section-aware, not fixed-width. Chunking strategy is an
  explicit experiment with measured outcomes, not a default.
- **Metadata per chunk (mandatory, enables citation):**
  `{ company, ticker, doc_type, fiscal_year, page_no, section_heading, chunk_id }`

**Orchestration:** Temporal, introduced here in Phase 2. Ingestion is
long-running, partially failing and resumable — exactly what durable workflows
are for, and it leverages existing expertise rather than learning a new
orchestrator. Phase 4 extends the same Temporal deployment to agent workflows;
it is not a new dependency at that point.

### 5.4 Hybrid retrieval

Built from primitives. No RAG framework in this path.

1. **Query transformation** — multi-query expansion and/or HyDE.
2. **Dense retrieval** — pgvector. HNSW parameters tuned deliberately and
   the tuning documented.
3. **Sparse retrieval** — Elasticsearch BM25. Financial queries are full of
   exact terms (scheme names, section headings, "related party") where
   lexical matching outperforms embeddings.
4. **Fusion** — reciprocal rank fusion over both result sets.
5. **Reranking** — cross-encoder over the fused candidate set.

Each stage is independently measurable, which is what makes stage-by-stage
evaluation possible in §6.

### 5.5 Agent layer

**Tools exposed to the analyst agent:**

| Tool | Returns | Nature |
|---|---|---|
| `get_fundamentals(ticker)` | structured JSON | deterministic |
| `search_filings(ticker, query)` | cited chunks | RAG |
| `web_search(query)` | URLs + snippets | external |
| `get_past_thesis(ticker)` | prior analysis | log retrieval |

**Two-stage agentic pattern:**
1. **Analyst** produces a stance with evidence.
2. **Red-team critic** — a *separate* call with an adversarial system prompt —
   receives the analyst's output and argues against it, specifically hunting
   for the most damaging contrary evidence.

The critic being a separate call, not an instruction inside one prompt, is
deliberate: self-critique within a single generation is measurably weaker,
and the separation makes the critique independently evaluable.

### 5.6 Grounding validator — the hard gate

This is the component that makes the system trustworthy, and it is code, not
a prompt instruction.

**Numeric grounding.** Extract every numeric token from model output. Assert
each appears in the structured payload passed in. Any number that does not
resolve is a **hard failure**, surfaced loudly, not silently rendered.

Two clarifications that would otherwise bite during implementation:

- **Derived values are pre-computed, never left to the model.** Allocation
  percentages, concentration ratios, weighted averages and gain/loss figures
  are all calculated deterministically in Python and included in the payload
  before the call. The model is never permitted to do arithmetic, which keeps
  the grounding rule absolute rather than carving out exceptions for
  "reasonable" derivations.
- **Matching normalizes rounding.** A payload value of `17.34` must accept
  `17.3` and `17` in prose. Matching compares against the payload value at a
  stated tolerance; it is not naive string equality, or the validator would
  fire constantly on correct output.

**Citation grounding.** Every citation must resolve to a real `chunk_id` that
was actually retrieved in this request. URLs are carried through from search
results by code; the model never emits a URL that code did not supply.

**Contract validation.** Output must parse against the expected schema, must
contain a non-empty red-team section, and `governance_checked` defaults to
`false` and can never be set true by the model.

### 5.7 Web layer

FastAPI, server-rendered templates, Chart.js from CDN. No SPA, no build step.
Roughly five routes. Deliberately boring — the engineering interest lives
below it, and a build pipeline here would add setup friction for anyone
self-hosting.

---

## 6. Evaluation strategy

This section is the difference between "I used a vector DB" and "I can
engineer retrieval," and it is the primary career artifact.

**Golden set.** Hand-built question → expected-source-chunk pairs over the
filings corpus, weighted toward governance questions ("were there auditor
qualifications in FY25?", "what related-party transactions were disclosed?").
Target ~50-100 pairs. Building this by hand is tedious and non-negotiable.

**Retrieval metrics:** recall@k, MRR, nDCG — measured at each stage, so the
marginal contribution of fusion and of reranking is isolated and reported.

**Generation metrics:** faithfulness (is every claim supported by retrieved
context), citation accuracy (do citations point at chunks that actually
support the claim), and refusal correctness (does it say "not available"
rather than inventing, when the corpus lacks the answer).

**Regression suite in CI.** GitHub Actions. Prompt and retrieval changes that
degrade metrics fail the build. Prompts are versioned like code.

---

## 7. Observability

Per-call tracing: prompt version, token counts, cost, latency, tools invoked,
chunks retrieved, validator outcome. Exported to Prometheus, visualized in
Grafana. Cost per portfolio review is a tracked, reported number.

---

## 8. Phasing

Each phase ends in something that works and is worth writing about.

| Phase | Deliverable | Learning focus |
|---|---|---|
| **0** | Holdings → canonical schema → cached snapshot → dashboard. No AI. | Connector design, cache-on-expiry |
| **1** | Structured fast pass + grounding validator + tests | Structured outputs, hallucination gating |
| **2** | RAG core: ingest (on Temporal) → pgvector + BM25 → RRF → rerank → citations | **The retrieval centerpiece** |
| **3** | Golden set + eval harness + CI regression | **The employability multiplier** |
| **4** | Agentic deep dive: tool-calling analyst + red-team critic, reusing the Phase 2 Temporal deployment | Agent orchestration, durable workflows |
| **5** | Observability, cost/latency, public architecture writeup | Production AI discipline |

Phases 0-3 are the core. 4-5 are what make it senior-looking.

Assumed pace: evenings and weekends, Phases 0-3 over roughly two to three
months.

---

## 9. Key decisions and rejected alternatives

### 9.1 Primitives over a RAG framework
LlamaIndex/LangChain reach a working pipeline far faster. Rejected for the
core retrieval path because the abstractions hide precisely the mechanics
this project exists to learn, and because the resume already claims RAG — it
needs to survive interview probing, where `.as_query_engine()` is a bad
answer. A framework port as an explicit comparison remains a possible later
phase.

### 9.2 pgvector + Elasticsearch over Pinecone
Pinecone is already on the resume and hides index internals. Self-hosting
teaches HNSW tuning and index tradeoffs, and Elasticsearch is existing
expertise reused for the sparse half of hybrid retrieval.

### 9.3 OpenAlgo over direct broker integration
Broker auth across many brokers is a maintenance treadmill that OpenAlgo
already solved well (34+ brokers). Nivesh consumes its unified local REST
API and inherits multi-broker support without owning credentials.

### 9.4 Separate critic call over single-prompt self-critique
See 5.5.

### 9.5 Anthropic-only in v1
One provider, the user's own key. Provider-agnostic routing is a later
phase; multi-provider prompt divergence is a distraction from the retrieval
and evaluation work that matters here.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| PDF table parsing consumes the project | Timebox; degrade to text-only chunks and narrow the corpus if needed |
| Golden set construction is tedious and gets skipped | It is a numbered phase with its own deliverable, not a task inside another phase |
| Broker session expiry makes the tool feel broken | Snapshot cache + explicit staleness banner (5.1) |
| Scope creep into MFs, history, multi-provider | Explicit non-goals (§2); each is a named later phase |
| LLM cost during evaluation runs | Cached fixtures for regression tests; live calls only in the golden-set run |

---

## 11. Legal and publication framing

The system emits stance language (buy/hold/avoid) on named Indian securities.
SEBI regulates investment advice. As a private tool this is unproblematic; as
a public repository with accompanying LinkedIn posts, framing matters.

Requirements:
- `LIMITATIONS.md` is a first-class repository file, not a footnote.
- README and all public posts frame the project as **research tooling for the
  author's own due diligence**, never as advice or recommendations.
- The author's own stance outputs are not published as content.
- Public writeups lead with the engineering (retrieval, evaluation, agents),
  not with stock picks.

---

## 12. Open questions

1. Web search provider for the `web_search` tool — Anthropic's built-in tool
   was assumed but availability and cost are unverified. Keep it behind an
   interface so it is swappable.
2. Filings source — exchange announcement APIs versus company IR pages;
   coverage and reliability unknown, needs a spike.
3. Embedding model choice — dimensionality, cost and Indian-financial-English
   performance. A candidate for a measured comparison in Phase 2.
4. Repository name — `nivesh` is a working title.
