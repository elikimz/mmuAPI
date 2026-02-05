from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.weathfundschedular import start_scheduler
from app.routers import auth,deposit,withdrawal,levels,task,userlevels,usertask,wealthfund,userweathfund,referals,profile,earnings,me,news

app = FastAPI()

# ----------------------------
# CORS Middleware (updated)
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ only for testing!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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



@app.get("/")
async def root():
    return {"message": "Api is running!"}

@app.on_event("startup")
async def on_startup():
    start_scheduler()