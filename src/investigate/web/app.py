import os

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from investigate.engine.portfolio import get_current_portfolio

app = FastAPI()
# Assuming the package structure is src/investigate/web/templates
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
