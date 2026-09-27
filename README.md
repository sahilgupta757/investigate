# InvestiGate

InvestiGate is a robust portfolio dashboard connecting to the OpenAlgo trading API. It aims to fetch, normalize, and visualize your holdings across multiple brokers.

## Architecture

- **Backend:** FastAPI + Pydantic v2
- **Orchestration:** Docker Compose
- **Resilience:** Fallback cache logic to ensure data is displayed even if the broker session expires.

*Currently in Phase 0: Basic holdings fetch and caching from OpenAlgo.*
