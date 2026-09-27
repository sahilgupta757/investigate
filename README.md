# InvestiGate

*invest + investigate — "Investigate before you invest."*

An agentic RAG system for Indian equity research. Reads a real brokerage
portfolio, grounds its analysis in primary source documents (annual reports,
filings, earnings-call transcripts), and produces a portfolio review where
every number is traceable to a deterministic source and every qualitative
claim carries a citation.

---

## What This Is

A **personal research tool** for the author's own investment due diligence.
This is not investment advice, not a recommendation engine, and not a
financial product. See [LIMITATIONS.md](LIMITATIONS.md).

It is also an **applied AI engineering project** — built to learn and
demonstrate retrieval, evaluation, agent orchestration, and grounding from
primitives, not from framework abstractions.

## Architecture

```
Portfolio (OpenAlgo) → Connector → Cached Snapshot → Dashboard
                                        │
        yfinance / APIs ───────────────▶│  Facts payload (structured JSON)
                                        │
        Filings, annual reports ──────▶ Ingestion (LangGraph)
                                        │  parse → chunk → embed
                                        ▼
                               Hybrid Index (Postgres)
                               pgvector + Elasticsearch BM25
                               → RRF → cross-encoder rerank
                                        │
                               Agent Layer (LangGraph)
                               analyst → red-team critic
                                        │
                               Grounding Validator (hard gate)
                                        │
                               FastAPI + server-rendered dashboard
```

**Core principle:** The analysis engine is a plain Python package with no web
dependency. FastAPI is a thin wrapper. The engine is independently testable.

## Key Design Decisions

- **RAG for governance only** — auditor qualifications, promoter pledging,
  related-party transactions, contingent liabilities. These exist only as
  prose in 100–300 page PDFs and are not available from any structured API.
- **Numbers are never embedded** — structured data is fetched deterministically
  and passed as JSON. Vector search over numbers degrades precision and
  increases hallucination risk.
- **No RAG framework in the retrieval path** — pgvector queries, BM25, RRF
  fusion, and reranking are all hand-written. LangGraph orchestrates but
  does not retrieve.
- **Separate critic call** — red-team critique is a separate LLM call with an
  adversarial system prompt, not in-context self-critique.
- **Grounding validator is code, not a prompt** — every number must trace to
  the structured payload; every citation must resolve to a retrieved chunk.

## Phasing

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **0** | Holdings → schema → cache → dashboard (no AI, no DB) | 🔲 |
| **1** | Structured fast pass + grounding validator + tests | 🔲 |
| **2** | RAG core: ingest → pgvector + BM25 → RRF → rerank → citations | 🔲 |
| **3** | Golden set + eval harness + CI regression | 🔲 |
| **4** | Agentic deep dive: analyst + red-team critic | 🔲 |
| **5** | Observability, cost/latency, public writeup | 🔲 |

## Tech Stack

- Python 3.12+, LangGraph + LangChain, PostgreSQL + pgvector, Elasticsearch,
  PyMuPDF, FastAPI, Anthropic Claude, OpenAlgo

## Setup

```bash
# Coming in Phase 0
```

## License

MIT

---

> **Disclaimer:** This tool is for personal research and educational purposes
> only. It is not investment advice. See [LIMITATIONS.md](LIMITATIONS.md).
