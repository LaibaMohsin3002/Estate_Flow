import asyncio
import logging

import httpx

# Monkeypatch httpx to disable HTTP/2 globally.
# This prevents sporadic "httpx.RemoteProtocolError: Server disconnected" exceptions
# caused by Supabase/Kong gateway terminating idle HTTP/2 multiplexed connections.
original_client_init = httpx.Client.__init__
def patched_client_init(self, *args, **kwargs):
    kwargs["http2"] = False
    original_client_init(self, *args, **kwargs)
httpx.Client.__init__ = patched_client_init

original_async_client_init = httpx.AsyncClient.__init__
def patched_async_client_init(self, *args, **kwargs):
    kwargs["http2"] = False
    original_async_client_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = patched_async_client_init

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.predictive_maintenance import run_predictive_maintenance_batch
from app.api.routes import (
    calendar,
    health,
    inspections,
    knowledge,
    maintenance,
    notifications,
    predictive,
    profile,
    properties,
    vendors,
)
from app.config import get_settings

logger = logging.getLogger(__name__)

def _cors_origins() -> list[str]:
    return [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]

app = FastAPI(
    title="EstateFlow API",
    description="Multi-agent property management platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(profile.router, prefix="/api")
app.include_router(properties.router, prefix="/api")
app.include_router(vendors.router, prefix="/api")
app.include_router(calendar.router, prefix="/api")
app.include_router(maintenance.router, prefix="/api")
app.include_router(inspections.router, prefix="/api")
app.include_router(predictive.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")


async def _vendor_followup_loop() -> None:
    """Reassign unresolved vendor complaints when the 24-hour follow-up window expires."""
    await asyncio.sleep(30)
    while True:
        try:
            processed = await vendors.process_pending_vendor_followups()
            logger.info("Vendor follow-up batch processed %s requests", processed)
        except Exception:
            logger.exception("Vendor follow-up batch failed")
        await asyncio.sleep(3600)


async def _predictive_weekly_loop() -> None:
    """Predictive Maintenance Agent (#12) — runs weekly in the background."""
    interval_sec = 7 * 24 * 3600
    await asyncio.sleep(120)  # let API start before first scheduled run
    while True:
        try:
            stats = await run_predictive_maintenance_batch()
            logger.info("Predictive maintenance batch: %s", stats)
        except Exception:
            logger.exception("Predictive maintenance batch failed")
        await asyncio.sleep(interval_sec)


@app.on_event("startup")
async def startup_predictive_scheduler() -> None:
    app.state.background_tasks = [
        asyncio.create_task(_predictive_weekly_loop()),
        asyncio.create_task(_vendor_followup_loop()),
    ]


@app.get("/")
async def root():
    return {"service": "EstateFlow", "docs": "/docs"}
