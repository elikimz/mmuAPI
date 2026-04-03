"""
UKB API — FastAPI application entry point.

Azure App Service deployment notes:
  - Startup command: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
  - Required App Settings (Configuration > Application Settings):
      DATABASE_URL  = postgresql+asyncpg://<user>:<pass>@<host>/<db>
      SECRET_KEY    = <your-secret-key>
  - APScheduler requires a single-worker deployment (--workers 1) because the
    in-process scheduler does not coordinate across multiple OS processes.
  - Redis is optional; connection failures are logged as warnings, not errors.
"""
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.taskschedular import start_task_scheduler
from app.core.weathfundschedular import start_scheduler
from app.routers import (
    auth, deposit, withdrawal, levels, task, userlevels, usertask,
    wealthfund, userweathfund, referals, profile, earnings, me, news,
    giftcode, spinwheel, cotacts, countdown, websocket, admin_dashboard,
)

# ─── Logging Configuration ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ukbAPI")


# ─── Lifespan (replaces deprecated @app.on_event) ────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Startup: connect Redis (non-fatal), start APScheduler jobs.
    Shutdown: disconnect Redis gracefully.
    """
    logger.info("Starting UKB API...")

    # Redis — non-fatal: app works without it
    try:
        from app.core.redis_cache import cache
        await cache.connect()
        logger.info("Redis cache connected.")
    except Exception as e:
        logger.warning(f"Redis cache connection failed (non-fatal): {e}")

    # Wealth fund scheduler
    try:
        start_scheduler()
        logger.info("Wealth fund scheduler started.")
    except Exception as e:
        logger.error(f"Failed to start wealth fund scheduler: {e}")

    # Task / level-expiry scheduler
    try:
        start_task_scheduler()
        logger.info("Task scheduler started.")
    except Exception as e:
        logger.error(f"Failed to start task scheduler: {e}")

    logger.info("UKB API startup complete.")

    yield  # ← application runs here

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down UKB API...")
    try:
        from app.core.redis_cache import cache
        await cache.close()
        logger.info("Redis cache disconnected.")
    except Exception as e:
        logger.warning(f"Redis cache close failed: {e}")
    logger.info("UKB API shutdown complete.")


# ─── FastAPI Application ──────────────────────────────────────────────────────
app = FastAPI(
    title="UKB API",
    description="UKB Platform Backend API",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── CORS Middleware ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global Exception Handlers ────────────────────────────────────────────────
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    method = getattr(request, "method", "WS")
    logger.error(f"Database error on {method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred. Please try again later."},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception on {request.method} {request.url}: {exc}\n"
        + traceback.format_exc()
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(deposit.router)
app.include_router(withdrawal.router)
app.include_router(levels.router)
app.include_router(task.router)
app.include_router(userlevels.router)
app.include_router(usertask.router)
app.include_router(wealthfund.router)
app.include_router(userweathfund.router)
app.include_router(referals.router)
app.include_router(profile.router)
app.include_router(earnings.router)
app.include_router(me.router)
app.include_router(news.router)
app.include_router(giftcode.router)
app.include_router(spinwheel.router)
app.include_router(cotacts.router)
app.include_router(countdown.router)
app.include_router(websocket.router)
app.include_router(admin_dashboard.router)


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {"message": "API is running!", "status": "ok"}
