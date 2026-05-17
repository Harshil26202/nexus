"""NEXUS — AI-Native Engineering Intelligence Platform — API entrypoint."""
import contextlib
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis_client import redis_pool
from app.core.telemetry import setup_telemetry
from app.routers import (
    analytics,
    agents,
    chat,
    incidents,
    pipelines,
    quality_gates,
    webhooks,
    ws,
)

log = structlog.get_logger()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("nexus.startup", env=settings.ENVIRONMENT)
    setup_telemetry()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await redis_pool.initialize()
    log.info("nexus.ready")
    yield
    await redis_pool.close()
    await engine.dispose()
    log.info("nexus.shutdown")


app = FastAPI(
    title="NEXUS API",
    description="AI-Native Engineering Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Prometheus Metrics ───────────────────────────────────────────────────────
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics")

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(pipelines.router,     prefix="/api/v1/pipelines",     tags=["Pipelines"])
app.include_router(agents.router,        prefix="/api/v1/agents",         tags=["Agents"])
app.include_router(incidents.router,     prefix="/api/v1/incidents",      tags=["Incidents"])
app.include_router(quality_gates.router, prefix="/api/v1/quality-gates",  tags=["Quality Gates"])
app.include_router(analytics.router,     prefix="/api/v1/analytics",      tags=["Analytics"])
app.include_router(chat.router,          prefix="/api/v1/chat",           tags=["NL DevOps Chat"])
app.include_router(webhooks.router,      prefix="/api/v1/webhooks",       tags=["Webhooks"])
app.include_router(ws.router,            prefix="/ws",                    tags=["WebSocket"])


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "service": "nexus-api", "version": "1.0.0"}
