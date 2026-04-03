from fastapi import FastAPI

from app.api.dashboard import router as dashboard_router
from app.api.deal import router as deal_router
from app.api.events import router as events_router
from app.api.hubspot import router as hubspot_router
from app.api.prospect import router as prospect_router
from app.core.config import settings
from app.db.session import init_db

app = FastAPI(title=settings.app_name)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(hubspot_router)
app.include_router(prospect_router)
app.include_router(deal_router)
app.include_router(events_router)
app.include_router(dashboard_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
