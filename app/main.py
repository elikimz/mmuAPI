import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from app.core.taskschedular import start_task_scheduler
from app.core.weathfundschedular import start_scheduler
from app.routers import auth,deposit,withdrawal,levels,task,userlevels,usertask,wealthfund,userweathfund,referals,profile,earnings,me,news,giftcode,spinwheel,cotacts,countdown,websocket

# ─── Logging Configuration ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mmuAPI")

app = FastAPI(
    title="MMU API",
    description="MMU Platform Backend API",
    version="1.0.0",
)


# ─── CORS Middleware ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global Exception Handlers ───────────────────────────────────────────────
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error on {request.method} {request.url}: {exc}")
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

# ----------------------------
# Include Routers
# ----------------------------
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



@app.get("/", tags=["Health"])
async def root():
    return {"message": "API is running!", "status": "ok"}

@app.on_event("startup")
async def on_startup():
    logger.info("Starting MMU API...")
    try:
        from app.core.redis_cache import cache
        await cache.connect()
        logger.info("Redis cache connected.")
    except Exception as e:
        logger.warning(f"Redis cache connection failed (non-fatal): {e}")
    try:
        start_scheduler()
        logger.info("Wealth fund scheduler started.")
    except Exception as e:
        logger.error(f"Failed to start wealth fund scheduler: {e}")
    try:
        start_task_scheduler()
        logger.info("Task scheduler started.")
    except Exception as e:
        logger.error(f"Failed to start task scheduler: {e}")
    logger.info("MMU API startup complete.")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down MMU API...")
    try:
        from app.core.redis_cache import cache
        await cache.close()
        logger.info("Redis cache disconnected.")
    except Exception as e:
        logger.warning(f"Redis cache close failed: {e}")
    
