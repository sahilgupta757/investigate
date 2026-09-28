import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from investigate.engine.portfolio import get_current_portfolio
from investigate.engine.enrichment import build_facts_payload
from investigate.engine.prompts import generate_fast_pass
from investigate.engine.validator import HallucinationError

app = FastAPI()
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)

@app.get("/")
def dashboard(request: Request):
    openalgo_url = os.environ.get("OPENALGO_URL", "http://openalgo:5000")
    openalgo_api_key = os.environ.get("OPENALGO_API_KEY", "dummy")
    cache_path = os.environ.get("CACHE_PATH", "/app/data/cache.json")

    snapshot, is_stale = get_current_portfolio(openalgo_url, openalgo_api_key, cache_path)

    if snapshot is None:
        return templates.TemplateResponse(
            request=request, name="dashboard.html", context={"empty_state": True}
        )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "empty_state": False,
            "snapshot": snapshot,
            "is_stale": is_stale,
            "total_value": snapshot.total_value,
            "allocations": snapshot.allocations,
        },
    )

@app.post("/api/fast-pass")
def fast_pass():
    openalgo_url = os.environ.get("OPENALGO_URL", "http://openalgo:5000")
    openalgo_api_key = os.environ.get("OPENALGO_API_KEY", "dummy")
    cache_path = os.environ.get("CACHE_PATH", "/app/data/cache.json")
    openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")

    if not openrouter_api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is missing")

    snapshot, _ = get_current_portfolio(openalgo_url, openalgo_api_key, cache_path)
    if snapshot is None:
        raise HTTPException(status_code=400, detail="No portfolio data available")

    facts = build_facts_payload(snapshot)
    
    try:
        review = generate_fast_pass(facts, openrouter_api_key)
        return review.model_dump()
    except HallucinationError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")
