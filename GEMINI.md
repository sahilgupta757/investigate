# InvestiGate — Agent Rules

## Project
This is InvestiGate, an agentic RAG system for Indian equity research.
See [design spec](docs/specs/2026-09-21-investigate-design.md) for full architecture.

## Key Constraints
- **Never embed numbers** — structured data is fetched deterministically, passed as JSON.
- **No RAG framework in retrieval path** — write pgvector queries, BM25, RRF, reranking by hand.
  LangGraph orchestrates but does not retrieve.
- **Grounding validator is code** — every number traces to the structured payload,
  every citation resolves to a retrieved chunk. This is not a prompt instruction.
- **The analysis engine is a plain Python package** — no web dependency in the core.
  FastAPI is a thin wrapper.
- **Learning project** — prefer understanding over shortcuts. Explain trade-offs when asked.

## Code Style
- Python 3.12+, type hints everywhere
- Use `ruff` for linting and formatting
- Tests with `pytest`
- Docstrings on all public functions
